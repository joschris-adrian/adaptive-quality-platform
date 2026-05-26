import pytest
from services.rca.root_cause import RCAEngine, FailureRecord
from services.rca.similarity import (
    cosine_similarity, nearest_neighbours,
    similarity_clusters, _signal_vector,
)


# ── fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def engine():
    return RCAEngine()


def _signals(ml=0.7, rule=0.5, spam=0.2):
    return {
        "ml":        {"risk_probability": ml},
        "rule":      {"risk_probability": rule},
        "heuristic": {"signals": {"spam_patterns": spam}},
    }


def _add(engine, event_id, tier="standard", category="fraud",
         failure_type="false_positive", risk_score=0.7, signals=None,
         reviewer_id=None):
    engine.record_failure(
        event_id=event_id, tier=tier, category=category,
        failure_type=failure_type, risk_score=risk_score,
        signals=signals or _signals(), reviewer_id=reviewer_id,
    )


# ── record_failure ─────────────────────────────────────────────────────────

def test_record_failure_stored(engine):
    _add(engine, "e1")
    assert len(engine._failures) == 1


def test_record_failure_fields(engine):
    _add(engine, "e1", tier="expert", category="spam",
         failure_type="false_negative", risk_score=0.55)
    r = engine._failures[0]
    assert r.event_id     == "e1"
    assert r.tier         == "expert"
    assert r.category     == "spam"
    assert r.failure_type == "false_negative"
    assert r.risk_score   == 0.55


def test_record_multiple_failures(engine):
    for i in range(5):
        _add(engine, f"e{i}")
    assert len(engine._failures) == 5


# ── failure_mode_summary ───────────────────────────────────────────────────

def test_failure_mode_summary_empty(engine):
    result = engine.failure_mode_summary()
    assert result["total"] == 0


def test_failure_mode_summary_counts(engine):
    _add(engine, "e1", failure_type="false_positive")
    _add(engine, "e2", failure_type="false_positive")
    _add(engine, "e3", failure_type="false_negative")
    result = engine.failure_mode_summary()
    assert result["total"] == 3
    assert result["by_failure_type"]["false_positive"]["count"] == 2
    assert result["by_failure_type"]["false_negative"]["count"] == 1


def test_failure_mode_summary_rates(engine):
    _add(engine, "e1", failure_type="false_positive")
    _add(engine, "e2", failure_type="false_negative")
    result = engine.failure_mode_summary()
    assert result["by_failure_type"]["false_positive"]["rate"] == pytest.approx(0.5)


def test_failure_mode_summary_filters_by_tier(engine):
    _add(engine, "e1", tier="expert",   failure_type="false_positive")
    _add(engine, "e2", tier="standard", failure_type="false_negative")
    result = engine.failure_mode_summary(tier="expert")
    assert result["total"] == 1
    assert "false_positive" in result["by_failure_type"]


def test_failure_mode_summary_filters_by_category(engine):
    _add(engine, "e1", category="fraud", failure_type="false_positive")
    _add(engine, "e2", category="spam",  failure_type="false_negative")
    result = engine.failure_mode_summary(category="fraud")
    assert result["total"] == 1


def test_failure_mode_summary_by_tier_and_category(engine):
    _add(engine, "e1", tier="expert",   category="fraud")
    _add(engine, "e2", tier="standard", category="spam")
    result = engine.failure_mode_summary()
    assert "expert"   in result["by_tier"]
    assert "standard" in result["by_tier"]
    assert "fraud"    in result["by_category"]
    assert "spam"     in result["by_category"]


# ── signal_correlation ─────────────────────────────────────────────────────

def test_signal_correlation_returns_means(engine):
    _add(engine, "e1", signals=_signals(ml=0.8, rule=0.6, spam=0.3))
    _add(engine, "e2", signals=_signals(ml=0.6, rule=0.4, spam=0.1))
    result = engine.signal_correlation()
    assert "ml.risk_probability"   in result
    assert "rule.risk_probability"  in result
    assert result["ml.risk_probability"]["mean_on_failures"] == pytest.approx(0.7)


def test_signal_correlation_empty(engine):
    assert engine.signal_correlation() == {}


def test_signal_correlation_filters_by_failure_type(engine):
    _add(engine, "e1", failure_type="false_positive", signals=_signals(ml=0.9))
    _add(engine, "e2", failure_type="false_negative", signals=_signals(ml=0.3))
    fp_result = engine.signal_correlation(failure_type="false_positive")
    assert fp_result["ml.risk_probability"]["mean_on_failures"] == pytest.approx(0.9)


def test_signal_correlation_sample_count(engine):
    _add(engine, "e1", signals=_signals())
    _add(engine, "e2", signals=_signals())
    result = engine.signal_correlation()
    assert result["ml.risk_probability"]["sample_count"] == 2


# ── disagreement_patterns ─────────────────────────────────────────────────

def test_disagreement_patterns_empty(engine):
    result = engine.disagreement_patterns()
    assert result["total_disagreements"] == 0


def test_disagreement_patterns_counts(engine):
    _add(engine, "e1", failure_type="disagreement", category="fraud",   reviewer_id="r1")
    _add(engine, "e2", failure_type="disagreement", category="fraud",   reviewer_id="r2")
    _add(engine, "e3", failure_type="disagreement", category="spam",    reviewer_id="r1")
    result = engine.disagreement_patterns()
    assert result["total_disagreements"]          == 3
    assert result["by_category"]["fraud"]["count"] == 2
    assert result["by_category"]["spam"]["count"]  == 1


def test_disagreement_patterns_by_reviewer(engine):
    _add(engine, "e1", failure_type="disagreement", reviewer_id="r1")
    _add(engine, "e2", failure_type="disagreement", reviewer_id="r1")
    _add(engine, "e3", failure_type="disagreement", reviewer_id="r2")
    result = engine.disagreement_patterns()
    assert result["by_reviewer"]["r1"]["count"] == 2
    assert result["by_reviewer"]["r2"]["count"] == 1


def test_disagreement_patterns_ignores_other_failure_types(engine):
    _add(engine, "e1", failure_type="false_positive")
    _add(engine, "e2", failure_type="disagreement")
    result = engine.disagreement_patterns()
    assert result["total_disagreements"] == 1


# ── cluster_failures ───────────────────────────────────────────────────────

def test_cluster_failures_category_x_type(engine):
    _add(engine, "e1", category="fraud", failure_type="false_positive")
    _add(engine, "e2", category="fraud", failure_type="false_positive")
    _add(engine, "e3", category="spam",  failure_type="false_negative")
    clusters = engine.cluster_failures(strategy="category_x_type")
    assert "fraud::false_positive" in clusters
    assert clusters["fraud::false_positive"]["count"] == 2


def test_cluster_failures_tier_x_type(engine):
    _add(engine, "e1", tier="expert",   failure_type="false_negative")
    _add(engine, "e2", tier="standard", failure_type="false_positive")
    clusters = engine.cluster_failures(strategy="tier_x_type")
    assert "expert::false_negative"   in clusters
    assert "standard::false_positive" in clusters


def test_cluster_failures_risk_band_x_type(engine):
    _add(engine, "e1", failure_type="false_positive", risk_score=0.90)  # critical
    _add(engine, "e2", failure_type="false_positive", risk_score=0.30)  # low
    clusters = engine.cluster_failures(strategy="risk_band_x_type")
    assert "critical::false_positive" in clusters
    assert "low::false_positive"      in clusters


def test_cluster_failures_avg_risk_score(engine):
    _add(engine, "e1", risk_score=0.8, failure_type="false_positive", category="fraud")
    _add(engine, "e2", risk_score=0.6, failure_type="false_positive", category="fraud")
    clusters = engine.cluster_failures()
    assert clusters["fraud::false_positive"]["avg_risk_score"] == pytest.approx(0.7)


def test_cluster_failures_sample_event_ids(engine):
    for i in range(7):
        _add(engine, f"e{i}", category="fraud", failure_type="false_positive")
    clusters = engine.cluster_failures()
    assert len(clusters["fraud::false_positive"]["sample_event_ids"]) <= 5


# ── failure_rate_trend ─────────────────────────────────────────────────────

def test_failure_rate_trend_insufficient_data(engine):
    _add(engine, "e1")
    result = engine.failure_rate_trend(window_size=50)
    assert result["status"] == "insufficient_data"


def test_failure_rate_trend_stable(engine):
    for i in range(200):
        _add(engine, f"e{i}", failure_type="false_positive")
    result = engine.failure_rate_trend(window_size=50)
    assert result["status"] == "stable"


def test_failure_rate_trend_detects_drift(engine):
    for i in range(100):
        _add(engine, f"e{i}", failure_type="false_positive")
    for i in range(100, 200):
        _add(engine, f"e{i}", failure_type="false_negative")
    result = engine.failure_rate_trend(window_size=50)
    assert result["status"] == "drift_detected"
    assert "false_negative" in result["drifting"]


def test_failure_rate_trend_has_rate_keys(engine):
    for i in range(120):
        _add(engine, f"e{i}", failure_type="false_positive" if i < 60 else "false_negative")
    result = engine.failure_rate_trend(window_size=50)
    assert "early_rates"  in result
    assert "recent_rates" in result
    assert "deltas"       in result


# ── emerging_categories ────────────────────────────────────────────────────

def test_emerging_categories_insufficient_data(engine):
    _add(engine, "e1", category="fraud")
    result = engine.emerging_categories(window_size=50)
    assert result == []


def test_emerging_categories_detects_new(engine):
    # Early window: all fraud
    for i in range(100):
        _add(engine, f"e{i}", category="fraud")
    # Recent window: mix of fraud and new_attack_vector
    for i in range(100, 150):
        _add(engine, f"e{i}", category="fraud")
    for i in range(150, 200):
        _add(engine, f"e{i}", category="new_attack_vector")

    result = engine.emerging_categories(window_size=50)
    cats   = [r["category"] for r in result]
    assert "new_attack_vector" in cats

def test_emerging_categories_sorted_by_delta(engine):
    for i in range(100):
        _add(engine, f"e{i}", category="fraud")
    for i in range(100, 160):
        _add(engine, f"e{i}", category="new_cat_a")
    for i in range(160, 200):
        _add(engine, f"e{i}", category="new_cat_b")

    result = engine.emerging_categories(window_size=50)
    deltas = [r["delta"] for r in result]
    assert deltas == sorted(deltas, reverse=True)


# ── report ─────────────────────────────────────────────────────────────────

def test_report_structure(engine):
    _add(engine, "e1")
    report = engine.report()
    for key in ["generated_at", "total_failures", "failure_modes",
                "signal_correlation", "disagreement", "clusters",
                "trend", "emerging_categories"]:
        assert key in report


def test_report_total_failures(engine):
    _add(engine, "e1")
    _add(engine, "e2")
    report = engine.report()
    assert report["total_failures"] == 2


# ── cosine_similarity ─────────────────────────────────────────────────────

def test_cosine_similarity_identical(engine):
    a = {"x": 1.0, "y": 0.5}
    assert cosine_similarity(a, a) == pytest.approx(1.0)


def test_cosine_similarity_orthogonal():
    a = {"x": 1.0, "y": 0.0}
    b = {"x": 0.0, "y": 1.0}
    assert cosine_similarity(a, b) == pytest.approx(0.0)


def test_cosine_similarity_zero_vector():
    a = {"x": 0.0}
    b = {"x": 1.0}
    assert cosine_similarity(a, b) == 0.0


def test_cosine_similarity_partial_overlap():
    a = {"x": 1.0, "y": 0.0}
    b = {"x": 1.0, "z": 1.0}
    sim = cosine_similarity(a, b)
    assert 0.0 < sim < 1.0


# ── nearest_neighbours ────────────────────────────────────────────────────

def _make_record(event_id, ml=0.7, rule=0.5, spam=0.2,
                 failure_type="false_positive", category="fraud"):
    return FailureRecord(
        event_id=event_id, tier="standard", category=category,
        failure_type=failure_type, risk_score=ml,
        signals=_signals(ml=ml, rule=rule, spam=spam),
    )


def test_nearest_neighbours_returns_top_n():
    target = _make_record("t", ml=0.8, rule=0.6)
    pool   = [_make_record(f"e{i}", ml=0.8, rule=0.6) for i in range(10)]
    result = nearest_neighbours(target, pool, top_n=3)
    assert len(result) <= 3


def test_nearest_neighbours_excludes_target():
    target = _make_record("t")
    pool   = [target, _make_record("e1")]
    result = nearest_neighbours(target, pool)
    ids    = [r["event_id"] for r in result]
    assert "t" not in ids


def test_nearest_neighbours_min_similarity_filter():
    target = _make_record("t", ml=0.9, rule=0.9, spam=0.9)
    pool   = [_make_record("e1", ml=0.0, rule=0.0, spam=0.0)]
    result = nearest_neighbours(target, pool, min_sim=0.5)
    assert result == []


def test_nearest_neighbours_sorted_by_similarity():
    target = _make_record("t", ml=0.9)
    pool   = [
        _make_record("high", ml=0.9),
        _make_record("low",  ml=0.1),
    ]
    result = nearest_neighbours(target, pool, min_sim=0.0)
    sims   = [r["similarity"] for r in result]
    assert sims == sorted(sims, reverse=True)


# ── similarity_clusters ───────────────────────────────────────────────────

def test_similarity_clusters_groups_similar():
    records = [
        _make_record(f"e{i}", ml=0.8, rule=0.6, spam=0.1)
        for i in range(4)
    ]
    clusters = similarity_clusters(records, threshold=0.9)
    assert len(clusters) == 1
    assert len(clusters[0]) == 4


def test_similarity_clusters_separates_different():
    group_a = [_make_record(f"a{i}", ml=0.9, rule=0.9, spam=0.0) for i in range(3)]
    group_b = [_make_record(f"b{i}", ml=0.0, rule=0.0, spam=1.0) for i in range(3)]
    clusters = similarity_clusters(group_a + group_b, threshold=0.8)
    assert len(clusters) >= 2


def test_similarity_clusters_single_record():
    record   = [_make_record("e1")]
    clusters = similarity_clusters(record)
    assert len(clusters) == 1
    assert clusters[0] == ["e1"]