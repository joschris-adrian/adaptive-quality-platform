import pytest
from services.analytics.metrics import QualityAnalyticsEngine, DecisionRecord


@pytest.fixture
def engine():
    return QualityAnalyticsEngine()


def _fill_engine(engine, n_tp=40, n_fp=10, n_tn=30, n_fn=20,
                 tier="standard", category="fraud", start=0):
    i = start
    for _ in range(n_tp):
        engine.record_decision(f"evt-{i}", tier, category, "positive", 0.8)
        engine.record_ground_truth(f"evt-{i}", "positive")
        i += 1
    for _ in range(n_fp):
        engine.record_decision(f"evt-{i}", tier, category, "positive", 0.6)
        engine.record_ground_truth(f"evt-{i}", "negative")
        i += 1
    for _ in range(n_tn):
        engine.record_decision(f"evt-{i}", tier, category, "negative", 0.2)
        engine.record_ground_truth(f"evt-{i}", "negative")
        i += 1
    for _ in range(n_fn):
        engine.record_decision(f"evt-{i}", tier, category, "negative", 0.3)
        engine.record_ground_truth(f"evt-{i}", "positive")
        i += 1
    return i   # return next available offset


# ── record_decision / record_ground_truth ──────────────────────────────────

def test_record_decision_stored(engine):
    engine.record_decision("evt-001", "standard", "fraud", "positive", 0.8)
    assert len(engine._records) == 1


def test_record_ground_truth_updates_record(engine):
    engine.record_decision("evt-001", "standard", "fraud", "positive", 0.8)
    engine.record_ground_truth("evt-001", "positive")
    assert engine._records[0].ground_truth == "positive"


def test_record_ground_truth_unknown_event_raises(engine):
    with pytest.raises(KeyError):
        engine.record_ground_truth("does-not-exist", "positive")


def test_record_reversal_marks_record(engine):
    engine.record_decision("evt-001", "standard", "fraud", "positive", 0.8)
    engine.record_reversal("evt-001")
    assert engine._records[0].reversed is True


# ── precision_recall ───────────────────────────────────────────────────────

def test_precision_recall_correct_values(engine):
    _fill_engine(engine, n_tp=40, n_fp=10, n_tn=30, n_fn=20)
    m = engine.precision_recall()
    assert m["precision"] == pytest.approx(40 / 50, abs=1e-4)
    assert m["recall"]    == pytest.approx(40 / 60, abs=1e-4)


def test_precision_recall_empty_returns_zeros(engine):
    m = engine.precision_recall()
    assert m["precision"] == 0.0
    assert m["recall"]    == 0.0


def test_precision_recall_filters_by_tier(engine):
    next_i = _fill_engine(engine, n_tp=10, n_fp=0, tier="expert",   category="fraud", start=0)
    _fill_engine(engine, n_tp=5, n_fp=5,  tier="standard", category="fraud", start=next_i)
    m_expert = engine.precision_recall(tier="expert")
    assert m_expert["precision"] == pytest.approx(1.0)


def test_precision_recall_filters_by_category(engine):
    next_i = _fill_engine(engine, n_tp=10, n_fp=0, tier="standard", category="fraud", start=0)
    _fill_engine(engine, n_tp=5, n_fp=5,  tier="standard", category="spam",  start=next_i)
    m_fraud = engine.precision_recall(category="fraud")
    assert m_fraud["precision"] == pytest.approx(1.0)
    

def test_false_positive_rate(engine):
    _fill_engine(engine, n_tp=0, n_fp=10, n_tn=90, n_fn=0)
    m = engine.precision_recall()
    assert m["false_positive_rate"] == pytest.approx(10 / 100, abs=1e-4)


def test_false_negative_rate(engine):
    _fill_engine(engine, n_tp=80, n_fp=0, n_tn=0, n_fn=20)
    m = engine.precision_recall()
    assert m["false_negative_rate"] == pytest.approx(20 / 100, abs=1e-4)


def test_f1_score_computed(engine):
    _fill_engine(engine, n_tp=40, n_fp=10, n_tn=30, n_fn=20)
    m = engine.precision_recall()
    p, r = m["precision"], m["recall"]
    assert m["f1"] == pytest.approx(2 * p * r / (p + r), abs=1e-4)


def test_support_count(engine):
    _fill_engine(engine, n_tp=10, n_fp=5, n_tn=5, n_fn=5)
    m = engine.precision_recall()
    assert m["support"] == 25


# ── escalation_rate ────────────────────────────────────────────────────────

def test_escalation_rate_zero(engine):
    engine.record_decision("e1", "standard", "fraud", "positive", escalated=False)
    result = engine.escalation_rate()
    assert result["escalation_rate"] == 0.0


def test_escalation_rate_all(engine):
    engine.record_decision("e1", "expert", "fraud", "positive", escalated=True)
    engine.record_decision("e2", "expert", "fraud", "positive", escalated=True)
    result = engine.escalation_rate()
    assert result["escalation_rate"] == 1.0


def test_escalation_rate_filters_by_tier(engine):
    engine.record_decision("e1", "expert",   "fraud", "positive", escalated=True)
    engine.record_decision("e2", "standard", "fraud", "positive", escalated=False)
    result = engine.escalation_rate(tier="expert")
    assert result["escalation_rate"] == 1.0


# ── reversal_rate ──────────────────────────────────────────────────────────

def test_reversal_rate_zero_initially(engine):
    engine.record_decision("e1", "standard", "fraud", "positive")
    assert engine.reversal_rate()["reversal_rate"] == 0.0


def test_reversal_rate_after_reversal(engine):
    engine.record_decision("e1", "standard", "fraud", "positive")
    engine.record_decision("e2", "standard", "fraud", "positive")
    engine.record_reversal("e1")
    result = engine.reversal_rate()
    assert result["reversal_rate"] == pytest.approx(0.5)


def test_reversal_rate_filters_by_category(engine):
    engine.record_decision("e1", "standard", "fraud", "positive")
    engine.record_decision("e2", "standard", "spam",  "positive")
    engine.record_reversal("e1")
    result = engine.reversal_rate(category="spam")
    assert result["reversal_rate"] == 0.0


# ── breakdown ──────────────────────────────────────────────────────────────

def test_breakdown_by_tier_keys(engine):
    engine.record_decision("e1", "standard", "fraud", "positive")
    engine.record_decision("e2", "expert",   "fraud", "positive")
    breakdown = engine.breakdown_by_tier()
    assert "standard" in breakdown
    assert "expert"   in breakdown


def test_breakdown_by_category_keys(engine):
    engine.record_decision("e1", "standard", "fraud", "positive")
    engine.record_decision("e2", "standard", "spam",  "positive")
    breakdown = engine.breakdown_by_category()
    assert "fraud" in breakdown
    assert "spam"  in breakdown


def test_breakdown_by_tier_structure(engine):
    engine.record_decision("e1", "standard", "fraud", "positive")
    breakdown = engine.breakdown_by_tier()
    assert "precision_recall" in breakdown["standard"]
    assert "escalation"       in breakdown["standard"]
    assert "reversal"         in breakdown["standard"]


# ── reviewer_agreement ─────────────────────────────────────────────────────

def test_reviewer_agreement_no_multi_reviewed(engine):
    engine.record_decision("e1", "standard", "fraud", "positive", reviewer_id="r1")
    result = engine.reviewer_agreement()
    assert result["agreement_rate"]       is None
    assert result["multi_reviewed_count"] == 0


def test_reviewer_agreement_full_agreement(engine):
    engine.record_decision("e1", "standard", "fraud", "positive", reviewer_id="r1")
    engine.record_decision("e1", "standard", "fraud", "positive", reviewer_id="r2")
    result = engine.reviewer_agreement()
    assert result["agreement_rate"]  == 1.0
    assert result["agreed_count"]    == 1


def test_reviewer_agreement_disagreement(engine):
    engine.record_decision("e1", "standard", "fraud", "positive",  reviewer_id="r1")
    engine.record_decision("e1", "standard", "fraud", "negative",  reviewer_id="r2")
    result = engine.reviewer_agreement()
    assert result["agreement_rate"] == 0.0
    assert result["disagreed_count"] == 1


# ── drift_report ───────────────────────────────────────────────────────────

def test_drift_report_insufficient_data(engine):
    _fill_engine(engine, n_tp=5, n_fp=2, n_tn=3, n_fn=1)
    result = engine.drift_report(window_size=100)
    assert result["status"] == "insufficient_data"


def test_drift_report_stable(engine):
    # Same pattern repeated — no drift
    for i in range(200):
        engine.record_decision(f"e{i}", "standard", "fraud",
                               "positive" if i % 2 == 0 else "negative", 0.7)
        engine.record_ground_truth(f"e{i}",
                               "positive" if i % 2 == 0 else "negative")
    result = engine.drift_report(window_size=50)
    assert result["status"] == "stable"


def test_drift_report_detects_drift(engine):
    # Early: high precision. Recent: low precision (many FP).
    for i in range(100):
        engine.record_decision(f"e{i}", "standard", "fraud", "positive", 0.9)
        engine.record_ground_truth(f"e{i}", "positive")   # all TP early

    for i in range(100, 200):
        engine.record_decision(f"e{i}", "standard", "fraud", "positive", 0.6)
        engine.record_ground_truth(f"e{i}", "negative")   # all FP recent

    result = engine.drift_report(window_size=100)
    assert result["status"]          == "drift_detected"
    assert result["precision_delta"] < -0.05


# ── snapshot / trend ───────────────────────────────────────────────────────

def test_snapshot_structure(engine):
    _fill_engine(engine, n_tp=10, n_fp=2, n_tn=8, n_fn=1)
    snap = engine.snapshot()
    for key in ["timestamp", "total_decisions", "labelled_count",
                "global_metrics", "escalation", "reversal",
                "by_tier", "by_category", "reviewer_agreement"]:
        assert key in snap


def test_snapshot_accumulates(engine):
    _fill_engine(engine)
    engine.snapshot()
    engine.snapshot()
    assert len(engine._snapshots) == 2


def test_trend_extracts_metric(engine):
    _fill_engine(engine)
    engine.snapshot()
    engine.snapshot()
    trend = engine.trend("precision")
    assert len(trend) == 2
    for point in trend:
        assert "timestamp" in point
        assert "value"     in point


def test_trend_empty_before_snapshots(engine):
    assert engine.trend("precision") == []