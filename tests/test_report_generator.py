import os
import json
import pytest
from unittest.mock import patch, MagicMock
from services.analytics.metrics  import QualityAnalyticsEngine
from services.rca.root_cause      import RCAEngine
from dashboards.report_generator  import ReportGenerator


@pytest.fixture
def quality_engine():
    e = QualityAnalyticsEngine()
    for i in range(20):
        predicted    = "positive" if i < 14 else "negative"
        ground_truth = "positive" if i < 16 else "negative"
        e.record_decision(f"e{i}", "standard", "fraud", predicted, 0.75,
                          escalated=(i % 3 == 0))
        e.record_ground_truth(f"e{i}", ground_truth)
    for i in range(20, 25):
        e.record_decision(f"e{i}", "standard", "fraud", "positive", 0.75)
        e.record_reversal(f"e{i}")
    return e


@pytest.fixture
def rca_engine():
    e = RCAEngine()
    signals = {"ml": {"risk_probability": 0.8}, "rule": {"risk_probability": 0.5}}
    for i in range(5):
        e.record_failure(f"f{i}", "standard", "fraud", "false_positive", 0.7, signals)
    for i in range(5, 8):
        e.record_failure(f"f{i}", "expert", "spam", "false_negative", 0.55, signals)
    return e


@pytest.fixture
def generator(quality_engine, rca_engine):
    return ReportGenerator(
        quality_engine=quality_engine,
        rca_engine=rca_engine,
        total_events=1_000,
    )


# ── generate ───────────────────────────────────────────────────────────────

def test_generate_returns_dict(generator):
    report = generator.generate()
    assert isinstance(report, dict)


def test_generate_has_all_top_level_keys(generator):
    report = generator.generate()
    for key in ["generated_at", "period", "quality_summary",
                "cost_summary", "rca_summary", "drift"]:
        assert key in report


def test_generate_quality_summary_keys(generator):
    report = generator.generate()
    qs     = report["quality_summary"]
    for key in ["precision", "recall", "f1", "false_positive_rate",
                "false_negative_rate", "escalation_rate", "reversal_rate",
                "by_tier", "by_category"]:
        assert key in qs


def test_generate_quality_metrics_in_range(generator):
    report = generator.generate()
    qs     = report["quality_summary"]
    for metric in ["precision", "recall", "f1",
                   "false_positive_rate", "false_negative_rate",
                   "escalation_rate", "reversal_rate"]:
        assert 0.0 <= qs[metric] <= 1.0


def test_generate_cost_summary_keys(generator):
    report = generator.generate()
    cs     = report["cost_summary"]
    assert "recommended_strategy" in cs
    assert "strategies"           in cs


def test_generate_cost_strategies_present(generator):
    report     = generator.generate()
    strategies = report["cost_summary"]["strategies"]
    for name in ["automation_only", "hybrid_balanced",
                 "hybrid_quality_first", "human_heavy"]:
        assert name in strategies


def test_generate_cost_strategy_has_fields(generator):
    report   = generator.generate()
    strategy = next(iter(report["cost_summary"]["strategies"].values()))
    assert "total_cost"       in strategy
    assert "quality_score"    in strategy
    assert "efficiency_ratio" in strategy


def test_generate_rca_summary_keys(generator):
    report = generator.generate()
    rc     = report["rca_summary"]
    for key in ["total_failures", "top_failure_modes",
                "emerging_categories", "drift_status"]:
        assert key in rc


def test_generate_rca_total_failures(generator, rca_engine):
    report = generator.generate()
    assert report["rca_summary"]["total_failures"] == len(rca_engine._failures)


def test_generate_top_failure_modes_max_three(generator):
    report = generator.generate()
    assert len(report["rca_summary"]["top_failure_modes"]) <= 3


def test_generate_drift_has_status(generator):
    report = generator.generate()
    assert "status" in report["drift"]


def test_generate_generated_at_is_string(generator):
    report = generator.generate()
    assert isinstance(report["generated_at"], str)


# ── save ───────────────────────────────────────────────────────────────────

def test_save_creates_file(generator, tmp_path):
    with patch("dashboards.report_generator.OUTPUT_DIR", str(tmp_path)):
        report   = generator.generate()
        filepath = generator.save(report)
    assert os.path.exists(filepath)


def test_save_file_is_valid_json(generator, tmp_path):
    with patch("dashboards.report_generator.OUTPUT_DIR", str(tmp_path)):
        report   = generator.generate()
        filepath = generator.save(report)
    with open(filepath) as f:
        loaded = json.load(f)
    assert "quality_summary" in loaded


def test_save_filename_contains_timestamp(generator, tmp_path):
    with patch("dashboards.report_generator.OUTPUT_DIR", str(tmp_path)):
        report   = generator.generate()
        filepath = generator.save(report)
    assert "report_" in os.path.basename(filepath)
    assert filepath.endswith(".json")


def test_save_creates_output_dir_if_missing(generator, tmp_path):
    nested = str(tmp_path / "nested" / "reports")
    with patch("dashboards.report_generator.OUTPUT_DIR", nested):
        report   = generator.generate()
        filepath = generator.save(report)
    assert os.path.exists(nested)


def test_save_returns_filepath_string(generator, tmp_path):
    with patch("dashboards.report_generator.OUTPUT_DIR", str(tmp_path)):
        report   = generator.generate()
        filepath = generator.save(report)
    assert isinstance(filepath, str)


# ── print_summary ──────────────────────────────────────────────────────────

def test_print_summary_runs_without_error(generator, capsys):
    report = generator.generate()
    generator.print_summary(report)
    captured = capsys.readouterr()
    assert "Adaptive Quality Platform" in captured.out


def test_print_summary_contains_precision(generator, capsys):
    report = generator.generate()
    generator.print_summary(report)
    captured = capsys.readouterr()
    assert "Precision" in captured.out


def test_print_summary_contains_recommended_strategy(generator, capsys):
    report = generator.generate()
    generator.print_summary(report)
    captured = capsys.readouterr()
    assert report["cost_summary"]["recommended_strategy"] in captured.out


def test_print_summary_contains_drift_status(generator, capsys):
    report = generator.generate()
    generator.print_summary(report)
    captured = capsys.readouterr()
    assert report["rca_summary"]["drift_status"] in captured.out


# ── _cost_summary ──────────────────────────────────────────────────────────

def test_cost_summary_recommended_is_valid_strategy(generator):
    summary = generator._cost_summary()
    assert summary["recommended_strategy"] in summary["strategies"]


def test_cost_summary_all_costs_positive(generator):
    summary = generator._cost_summary()
    for data in summary["strategies"].values():
        assert data["total_cost"] >= 0.0


def test_cost_summary_quality_scores_bounded(generator):
    summary = generator._cost_summary()
    for data in summary["strategies"].values():
        assert 0.0 <= data["quality_score"] <= 1.0


def test_cost_summary_efficiency_ratios_positive(generator):
    summary = generator._cost_summary()
    for data in summary["strategies"].values():
        assert data["efficiency_ratio"] >= 0.0