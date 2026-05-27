import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from services.mlflow.tracking import (
    log_experiment_run,
    log_threshold_sweep,
    log_drift_snapshot,
    log_ab_variant,
)


@patch("services.mlflow.tracking.mlflow")
def test_log_experiment_run_calls_mlflow(mock_mlflow):
    mock_run = MagicMock()
    mock_mlflow.start_run.return_value.__enter__ = lambda s: mock_run
    mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)

    log_experiment_run(
        experiment_name="test-exp",
        run_name="test-run",
        params={"strategy": "hybrid"},
        metrics={"quality": 0.81, "cost": 760.0},
    )

    mock_mlflow.set_experiment.assert_called_once_with("test-exp")
    mock_mlflow.start_run.assert_called_once_with(run_name="test-run")


@patch("services.mlflow.tracking.mlflow")
def test_log_experiment_run_with_tags(mock_mlflow):
    mock_mlflow.start_run.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock_mlflow.start_run.return_value.__exit__ = MagicMock(return_value=False)

    log_experiment_run(
        experiment_name="test-exp",
        run_name="tagged-run",
        params={},
        metrics={},
        tags={"experiment": "budget-constrained"},
    )

    mock_mlflow.set_tags.assert_called_once_with({"experiment": "budget-constrained"})


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_threshold_sweep(mock_log):
    log_threshold_sweep(
        threshold=0.80,
        results={"quality": 0.808, "cost": 760.0, "auto_pct": 0.70},
    )

    mock_log.assert_called_once()
    call_kwargs = mock_log.call_args[1] if mock_log.call_args[1] else {}
    call_args   = mock_log.call_args[0] if mock_log.call_args[0] else ()

    assert "threshold-sweep" in (call_kwargs.get("experiment_name", "") or call_args[0])


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_threshold_sweep_values(mock_log):
    log_threshold_sweep(
        threshold=0.65,
        results={"quality": 0.85, "cost": 2100.0, "auto_pct": 0.45},
    )
    _, kwargs = mock_log.call_args
    assert kwargs["params"]["threshold"] == 0.65
    assert kwargs["metrics"]["quality"] == 0.85
    assert kwargs["metrics"]["cost"] == 2100.0


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_drift_snapshot_detected(mock_log):
    report = {
        "status": "drift_detected",
        "precision_delta": -0.08,
        "recall_delta": -0.03,
        "emerging_categories": ["new_attack_vector", "unknown_pattern"],
    }
    log_drift_snapshot(report)

    _, kwargs = mock_log.call_args
    assert kwargs["metrics"]["precision_delta"] == -0.08
    assert kwargs["metrics"]["emerging_categories_count"] == 2
    assert kwargs["tags"]["status"] == "drift_detected"


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_drift_snapshot_no_drift(mock_log):
    report = {"status": "ok", "precision_delta": 0.01, "recall_delta": 0.0}
    log_drift_snapshot(report)

    _, kwargs = mock_log.call_args
    assert kwargs["metrics"]["emerging_categories_count"] == 0
    assert kwargs["tags"]["status"] == "ok"


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_ab_variant(mock_log):
    log_ab_variant(
        experiment_name="ab-routing-strategy",
        variant="treatment",
        params={"n_events": 200, "split": 0.5},
        metrics={"precision": 0.91, "cost_per_event": 1.2, "reversal_rate": 0.04},
    )

    _, kwargs = mock_log.call_args
    assert kwargs["experiment_name"] == "ab-routing-strategy"
    assert kwargs["params"]["variant"] == "treatment"
    assert kwargs["metrics"]["precision"] == 0.91


@patch("services.mlflow.tracking.log_experiment_run")
def test_log_ab_variant_control(mock_log):
    log_ab_variant(
        experiment_name="ab-routing-strategy",
        variant="control",
        params={"n_events": 200, "split": 0.5},
        metrics={"precision": 0.82, "cost_per_event": 0.5, "reversal_rate": 0.08},
    )

    _, kwargs = mock_log.call_args
    assert kwargs["params"]["variant"] == "control"
    assert kwargs["metrics"]["reversal_rate"] == 0.08