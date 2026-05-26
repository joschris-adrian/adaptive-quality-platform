import pytest
from unittest.mock import patch
from services.risk_scoring.scorer import RiskScorer

MOCK_WEIGHTS = {
    "severity": {
        "fraud":            1.0,
        "policy_violation": 0.85,
        "abuse":            0.75,
        "spam":             0.55,
        "anomaly":          0.45,
        "unknown":          0.35,
        "clean":            0.05,
    },
    "exposure": {
        "event_type": {
            "transaction":         0.9,
            "moderation_decision": 0.7,
            "review_outcome":      0.6,
            "user_action":         0.4,
            "operational_alert":   0.3,
        },
        "source_system": {
            "api":    0.8,
            "mobile": 0.5,
            "web":    0.4,
        },
    },
    "priority_thresholds": {
        "critical": 0.85,
        "high":     0.65,
        "medium":   0.40,
    },
}


@pytest.fixture
def scorer():
    with patch("services.risk_scoring.scorer.load_weights", return_value=MOCK_WEIGHTS):
        return RiskScorer()


def _scored_event(risk_probability=0.8, category="fraud",
                  event_type="transaction", source_system="api",
                  ml_score=0.8, rule_score=0.8, heur_score=0.8):
    return {
        "event_id":         "evt-risk",
        "risk_probability": risk_probability,
        "category":         category,
        "signals": {
            "ml":        {"risk_probability": ml_score},
            "rule":      {"risk_probability": rule_score, "rules_triggered": ["blocklisted_user"]},
            "heuristic": {"risk_probability": heur_score, "signals": {"spam_patterns": 0.5}},
        },
        "source_event": {
            "event_type":    event_type,
            "source_system": source_system,
        },
    }


# --- Component computation ---

def test_severity_fraud(scorer):
    event = _scored_event(category="fraud")
    assert scorer._compute_severity(event) == 1.0


def test_severity_clean(scorer):
    event = _scored_event(category="clean")
    assert scorer._compute_severity(event) == 0.05


def test_severity_unknown_category_defaults(scorer):
    event = _scored_event(category="totally_new_category")
    assert scorer._compute_severity(event) == 0.2


def test_exposure_transaction_api(scorer):
    event    = _scored_event(event_type="transaction", source_system="api")
    exposure = scorer._compute_exposure(event)
    assert exposure == pytest.approx((0.9 + 0.8) / 2, abs=1e-4)


def test_exposure_unknown_defaults_to_mid(scorer):
    event    = _scored_event(event_type="unknown_type", source_system="unknown_sys")
    exposure = scorer._compute_exposure(event)
    assert exposure == pytest.approx(0.3, abs=1e-4)


def test_likelihood_agreement_bonus(scorer):
    event      = _scored_event(risk_probability=0.6, ml_score=0.8, rule_score=0.8, heur_score=0.8)
    likelihood = scorer._compute_likelihood(event)
    assert likelihood == pytest.approx(min(0.6 + 0.1, 1.0), abs=1e-4)


def test_likelihood_no_agreement_bonus(scorer):
    event      = _scored_event(risk_probability=0.6, ml_score=0.8, rule_score=0.3, heur_score=0.8)
    likelihood = scorer._compute_likelihood(event)
    assert likelihood == pytest.approx(0.6, abs=1e-4)


def test_likelihood_capped_at_one(scorer):
    event      = _scored_event(risk_probability=0.98, ml_score=0.9, rule_score=0.9, heur_score=0.9)
    likelihood = scorer._compute_likelihood(event)
    assert likelihood <= 1.0


# --- Priority assignment ---

def test_priority_critical(scorer):
    assert scorer._assign_priority(0.90) == "critical"


def test_priority_high(scorer):
    assert scorer._assign_priority(0.70) == "high"


def test_priority_medium(scorer):
    assert scorer._assign_priority(0.50) == "medium"


def test_priority_low(scorer):
    assert scorer._assign_priority(0.20) == "low"


def test_priority_boundary_critical(scorer):
    assert scorer._assign_priority(0.85) == "critical"


def test_priority_just_below_high(scorer):
    assert scorer._assign_priority(0.64) == "medium"


# --- Full score output ---

def test_score_returns_all_fields(scorer):
    result = scorer.score(_scored_event())
    assert "event_id"      in result
    assert "risk_score"    in result
    assert "priority"      in result
    assert "components"    in result
    assert "category"      in result
    assert "risk_metadata" in result


def test_score_components_present(scorer):
    result = scorer.score(_scored_event())
    assert "likelihood" in result["components"]
    assert "severity"   in result["components"]
    assert "exposure"   in result["components"]


def test_score_high_risk_event_is_critical_or_high(scorer):
    result = scorer.score(_scored_event(
        risk_probability=0.95, category="fraud",
        event_type="transaction", source_system="api",
        ml_score=0.95, rule_score=0.95, heur_score=0.95,
    ))
    assert result["priority"] in ("critical", "high")


def test_score_low_risk_event_is_low(scorer):
    result = scorer.score(_scored_event(
        risk_probability=0.05, category="clean",
        event_type="user_action", source_system="web",
        ml_score=0.05, rule_score=0.0, heur_score=0.0,
    ))
    assert result["priority"] == "low"


def test_metadata_requires_review_true_for_high(scorer):
    result = scorer.score(_scored_event(
        risk_probability=0.95, category="fraud",
        event_type="transaction", source_system="api",
        ml_score=0.95, rule_score=0.95, heur_score=0.95,
    ))
    assert result["risk_metadata"]["requires_review"] is True


def test_metadata_auto_actioned_true_for_low(scorer):
    result = scorer.score(_scored_event(
        risk_probability=0.05, category="clean",
        event_type="user_action", source_system="web",
        ml_score=0.05, rule_score=0.0, heur_score=0.0,
    ))
    assert result["risk_metadata"]["auto_actioned"] is True


def test_normalize_stays_in_range(scorer):
    for raw in [0.0, 0.1, 0.5, 0.9, 1.0]:
        result = scorer._normalize(raw)
        assert 0.0 <= result <= 1.0