import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.run_rca import engine, FAILURES, report


# ── fixtures ───────────────────────────────────────────────────────────────

def test_failures_list_not_empty():
    assert len(FAILURES) > 0


def test_all_failures_have_required_keys():
    required = {"event_id", "tier", "category", "failure_type", "risk_score", "signals"}
    for f in FAILURES:
        assert required.issubset(f.keys()), f"Missing keys in {f['event_id']}"


def test_failure_types_are_valid():
    valid = {"false_positive", "false_negative", "reversal", "disagreement"}
    for f in FAILURES:
        assert f["failure_type"] in valid


def test_risk_scores_in_range():
    for f in FAILURES:
        assert 0.0 <= f["risk_score"] <= 1.0


def test_signals_have_ml_key():
    for f in FAILURES:
        assert "ml" in f["signals"]


# ── engine state ───────────────────────────────────────────────────────────

def test_engine_has_correct_failure_count():
    assert len(engine._failures) == len(FAILURES)


def test_engine_failure_types_match_input():
    recorded_types = {r.failure_type for r in engine._failures}
    input_types    = {f["failure_type"] for f in FAILURES}
    assert recorded_types == input_types


def test_engine_categories_match_input():
    recorded_cats = {r.category for r in engine._failures}
    input_cats    = {f["category"] for f in FAILURES}
    assert recorded_cats == input_cats


def test_engine_reviewer_id_recorded():
    reviewers = [r.reviewer_id for r in engine._failures if r.reviewer_id]
    assert len(reviewers) >= 1


# ── report structure ───────────────────────────────────────────────────────

def test_report_has_all_keys():
    for key in ["generated_at", "total_failures", "failure_modes",
                "signal_correlation", "disagreement", "clusters",
                "trend", "emerging_categories"]:
        assert key in report


def test_report_total_failures_matches_input():
    assert report["total_failures"] == len(FAILURES)


def test_report_failure_modes_by_type_not_empty():
    assert len(report["failure_modes"]["by_failure_type"]) > 0


def test_report_failure_modes_by_category_not_empty():
    assert len(report["failure_modes"]["by_category"]) > 0


def test_report_failure_mode_rates_sum_to_one():
    rates = [
        d["rate"]
        for d in report["failure_modes"]["by_failure_type"].values()
    ]
    assert abs(sum(rates) - 1.0) < 1e-4


def test_report_signal_correlation_not_empty():
    assert len(report["signal_correlation"]) > 0


def test_report_signal_correlation_has_ml():
    keys = list(report["signal_correlation"].keys())
    assert any("ml" in k for k in keys)


def test_report_signal_correlation_means_positive():
    for sig, data in report["signal_correlation"].items():
        assert data["mean_on_failures"] >= 0.0


def test_report_clusters_not_empty():
    assert len(report["clusters"]) > 0


def test_report_clusters_have_required_keys():
    for cluster, data in report["clusters"].items():
        assert "count"           in data
        assert "avg_risk_score"  in data
        assert "sample_event_ids" in data


def test_report_clusters_counts_positive():
    for cluster, data in report["clusters"].items():
        assert data["count"] > 0


def test_report_fraud_false_positive_cluster_exists():
    assert "fraud::false_positive" in report["clusters"]


def test_report_disagreement_count_matches():
    disagreements_in_input = sum(
        1 for f in FAILURES if f["failure_type"] == "disagreement"
    )
    assert report["disagreement"]["total_disagreements"] == disagreements_in_input


def test_report_disagreement_by_reviewer_not_empty():
    assert len(report["disagreement"]["by_reviewer"]) > 0


def test_report_trend_has_status():
    assert "status" in report["trend"]


def test_report_emerging_categories_is_list():
    assert isinstance(report["emerging_categories"], list)


def test_report_generated_at_is_string():
    assert isinstance(report["generated_at"], str)