import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock, call
from services.mlflow.tracking import (
    log_experiment_run,
    log_threshold_sweep,
    log_drift_snapshot,
    log_ab_variant,
)


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_experiment_run_sets_experiment(mock_log):
    mock_log("my-exp", "my-run", {"p": 1}, {"m": 0.5})
    mock_log.assert_called_once_with("my-exp", "my-run", {"p": 1}, {"m": 0.5})


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_experiment_run_logs_params_and_metrics(mock_log):
    log_threshold_sweep(0.8, {"quality": 0.9, "cost": 760.0, "auto_pct": 0.70})
    _, kwargs = mock_log.call_args
    assert kwargs["metrics"]["quality"] == 0.9
    assert kwargs["metrics"]["cost"] == 760.0


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_experiment_run_skips_tags_when_none(mock_log):
    log_threshold_sweep(0.5, {"quality": 0.8, "cost": 100.0, "auto_pct": 0.5})
    _, kwargs = mock_log.call_args
    assert "tags" not in kwargs or kwargs.get("tags") is None


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_experiment_run_sets_tags_when_provided(mock_log):
    log_drift_snapshot({"status": "drift_detected", "precision_delta": -0.1,
                        "recall_delta": -0.05, "emerging_categories": []})
    _, kwargs = mock_log.call_args
    assert kwargs["tags"]["status"] == "drift_detected"


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_threshold_sweep_uses_correct_experiment(mock_log):
    log_threshold_sweep(0.75, {"quality": 0.82, "cost": 1100.0, "auto_pct": 0.62})
    mock_log.assert_called_once()
    _, kwargs = mock_log.call_args
    assert kwargs["experiment_name"] == "threshold-sweep"
    assert kwargs["run_name"] == "threshold_0.75"
    assert kwargs["params"]["threshold"] == 0.75


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_threshold_sweep_missing_keys_default_to_zero(mock_log):
    log_threshold_sweep(0.5, {})
    _, kwargs = mock_log.call_args
    assert kwargs["metrics"]["quality"] == 0
    assert kwargs["metrics"]["cost"] == 0
    assert kwargs["metrics"]["auto_pct"] == 0


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_drift_snapshot_stable(mock_log):
    report = {"status": "stable", "precision_delta": 0.01, "recall_delta": 0.0}
    log_drift_snapshot(report)
    _, kwargs = mock_log.call_args
    assert kwargs["tags"]["status"] == "stable"
    assert kwargs["metrics"]["precision_delta"] == 0.01
    assert kwargs["metrics"]["emerging_categories_count"] == 0


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_drift_snapshot_counts_emerging_categories(mock_log):
    report = {
        "status": "drift_detected",
        "precision_delta": -0.1,
        "recall_delta": -0.05,
        "emerging_categories": ["cat_a", "cat_b", "cat_c"],
    }
    log_drift_snapshot(report)
    _, kwargs = mock_log.call_args
    assert kwargs["metrics"]["emerging_categories_count"] == 3


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_ab_variant_includes_variant_in_params(mock_log):
    log_ab_variant("ab-exp", "control", {"split": 0.5}, {"precision": 0.82})
    _, kwargs = mock_log.call_args
    assert kwargs["params"]["variant"] == "control"
    assert kwargs["params"]["split"] == 0.5
    assert kwargs["metrics"]["precision"] == 0.82


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_ab_variant_run_name_includes_variant(mock_log):
    log_ab_variant("ab-exp", "treatment", {}, {})
    _, kwargs = mock_log.call_args
    assert kwargs["run_name"] == "variant_treatment"


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_ab_variant_passes_experiment_name(mock_log):
    log_ab_variant("my-ab-experiment", "control", {}, {})
    _, kwargs = mock_log.call_args
    assert kwargs["experiment_name"] == "my-ab-experiment"