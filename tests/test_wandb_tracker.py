import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock


@patch("services.wandb.tracker._wandb")
def test_init_run_calls_wandb_init(mock_wandb_fn):
    mock_wandb = MagicMock()
    mock_wandb_fn.return_value = mock_wandb

    from services.wandb.tracker import init_run
    init_run(project="test-project", run_name="test-run", config={"lr": 0.01})
    mock_wandb.init.assert_called_once_with(
        project="test-project", name="test-run", config={"lr": 0.01}, reinit=True
    )


@patch("services.wandb.tracker._wandb")
def test_log_metrics_calls_wandb_log(mock_wandb_fn):
    mock_wandb = MagicMock()
    mock_wandb_fn.return_value = mock_wandb

    from services.wandb.tracker import log_metrics
    log_metrics({"precision": 0.91, "recall": 0.88})
    mock_wandb.log.assert_called_once_with({"precision": 0.91, "recall": 0.88})


@patch("services.wandb.tracker._wandb")
def test_finish_calls_wandb_finish(mock_wandb_fn):
    mock_wandb = MagicMock()
    mock_wandb_fn.return_value = mock_wandb

    from services.wandb.tracker import finish
    finish()
    mock_wandb.finish.assert_called_once()


@patch("services.wandb.tracker._wandb")
def test_log_table_creates_table_and_logs(mock_wandb_fn):
    mock_wandb = MagicMock()
    mock_wandb_fn.return_value = mock_wandb

    from services.wandb.tracker import log_table
    log_table("false_positives", ["index", "score"], [[0, 0.72], [1, 0.68]])
    mock_wandb.Table.assert_called_once_with(
        columns=["index", "score"], data=[[0, 0.72], [1, 0.68]]
    )
    mock_wandb.log.assert_called_once()


@patch("services.wandb.tracker._wandb")
def test_log_model_creates_artifact(mock_wandb_fn):
    mock_wandb = MagicMock()
    mock_wandb_fn.return_value = mock_wandb

    from services.wandb.tracker import log_model
    log_model(None, "risk-classifier", metadata={"f1": 0.85})
    mock_wandb.Artifact.assert_called_once_with(
        "risk-classifier", type="model", metadata={"f1": 0.85}
    )
    mock_wandb.log_artifact.assert_called_once()


@patch("services.wandb.tracker._wandb")
def test_init_run_empty_config(mock_wandb_fn):
    mock_wandb = MagicMock()
    mock_wandb_fn.return_value = mock_wandb

    from services.wandb.tracker import init_run
    init_run(project="p", run_name="r")
    mock_wandb.init.assert_called_once_with(
        project="p", name="r", config={}, reinit=True
    )