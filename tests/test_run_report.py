import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from unittest.mock import patch
from scripts.run_report import quality, rca, generator, report


# ── quality engine state ───────────────────────────────────────────────────

def test_quality_engine_has_decisions():
    assert len(quality._records) > 0


def test_quality_engine_has_labelled_records():
    labelled = [r for r in quality._records if r.ground_truth is not None]
    assert len(labelled) > 0


def test_quality_engine_has_reversals():
    reversed_ = [r for r in quality._records if r.reversed]
    assert len(reversed_) > 0


def test_quality_engine_has_multiple_tiers():
    tiers = {r.tier for r in quality._records}
    assert len(tiers) >= 2


def test_quality_engine_has_multiple_categories():
    cats = {r.category for r in quality._records}
    assert len(cats) >= 2


def test_quality_engine_escalated_events_exist():
    escalated = [r for r in quality._records if r.escalated]
    assert len(escalated) > 0


# ── rca engine state ───────────────────────────────────────────────────────

def test_rca_engine_has_failures():
    assert len(rca._failures) > 0


def test_rca_engine_has_multiple_failure_types():
    types = {r.failure_type for r in rca._failures}
    assert len(types) >= 3


def test_rca_engine_has_fraud_failures():
    fraud = [r for r in rca._failures if r.category == "fraud"]
    assert len(fraud) > 0


def test_rca_engine_risk_scores_in_range():
    for r in rca._failures:
        assert 0.0 <= r.risk_score <= 1.0


# ── report structure ───────────────────────────────────────────────────────

def test_report_is_dict():
    assert isinstance(report, dict)


def test_report_has_all_sections():
    for key in ["generated_at", "period", "quality_summary",
                "cost_summary", "rca_summary", "drift"]:
        assert key in report


def test_report_precision_nonzero():
    assert report["quality_summary"]["precision"] > 0.0


def test_report_recall_nonzero():
    assert report["quality_summary"]["recall"] > 0.0


def test_report_f1_nonzero():
    assert report["quality_summary"]["f1"] > 0.0


def test_report_precision_in_range():
    assert 0.0 <= report["quality_summary"]["precision"] <= 1.0


def test_report_recall_in_range():
    assert 0.0 <= report["quality_summary"]["recall"] <= 1.0


def test_report_f1_in_range():
    assert 0.0 <= report["quality_summary"]["f1"] <= 1.0


def test_report_escalation_rate_in_range():
    assert 0.0 <= report["quality_summary"]["escalation_rate"] <= 1.0


def test_report_reversal_rate_in_range():
    assert 0.0 <= report["quality_summary"]["reversal_rate"] <= 1.0


def test_report_rca_total_failures_nonzero():
    assert report["rca_summary"]["total_failures"] > 0


def test_report_rca_total_failures_matches_engine():
    assert report["rca_summary"]["total_failures"] == len(rca._failures)


def test_report_cost_summary_has_recommended():
    assert "recommended_strategy" in report["cost_summary"]
    assert report["cost_summary"]["recommended_strategy"] is not None


def test_report_cost_strategies_all_present():
    strategies = report["cost_summary"]["strategies"]
    for name in ["automation_only", "hybrid_balanced",
                 "hybrid_quality_first", "human_heavy"]:
        assert name in strategies


def test_report_by_tier_not_empty():
    assert len(report["quality_summary"]["by_tier"]) > 0


def test_report_by_category_not_empty():
    assert len(report["quality_summary"]["by_category"]) > 0


def test_report_drift_has_status():
    assert "status" in report["drift"]


def test_report_generated_at_is_string():
    assert isinstance(report["generated_at"], str)


# ── generator ──────────────────────────────────────────────────────────────

def test_generator_save_creates_file(tmp_path):
    with patch("dashboards.report_generator.OUTPUT_DIR", str(tmp_path)):
        path = generator.save(report)
    assert os.path.exists(path)


def test_generator_save_is_valid_json(tmp_path):
    with patch("dashboards.report_generator.OUTPUT_DIR", str(tmp_path)):
        path = generator.save(report)
    with open(path) as f:
        loaded = json.load(f)
    assert "quality_summary" in loaded


def test_generator_print_summary_runs(capsys):
    generator.print_summary(report)
    captured = capsys.readouterr()
    assert "Adaptive Quality Platform" in captured.out
    assert "Precision" in captured.out


def test_generator_print_summary_shows_nonzero_precision(capsys):
    generator.print_summary(report)
    captured = capsys.readouterr()
    assert "0.0000" not in captured.out or "Precision" not in captured.out