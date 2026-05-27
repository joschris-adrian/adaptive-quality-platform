import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock
from services.mlflow.registry import register_model, promote_model, load_production_model


@patch("services.mlflow.registry.mlflow")
def test_register_model(mock_mlflow):
    register_model(run_id="abc123", model_name="risk-classifier")
    mock_mlflow.register_model.assert_called_once_with(
        "runs:/abc123/model", "risk-classifier"
    )


@patch("services.mlflow.registry.mlflow")
def test_register_model_custom_artifact_path(mock_mlflow):
    register_model(run_id="abc123", model_name="risk-classifier", artifact_path="my_model")
    mock_mlflow.register_model.assert_called_once_with(
        "runs:/abc123/my_model", "risk-classifier"
    )


@patch("services.mlflow.registry.MlflowClient")
def test_promote_model(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    promote_model(model_name="risk-classifier", version=1, stage="Production")

    mock_client.transition_model_version_stage.assert_called_once_with(
        name="risk-classifier",
        version=1,
        stage="Production",
        archive_existing_versions=True,
    )


@patch("services.mlflow.registry.MlflowClient")
def test_promote_model_staging(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client

    promote_model(model_name="risk-classifier", version=2, stage="Staging")

    mock_client.transition_model_version_stage.assert_called_once_with(
        name="risk-classifier",
        version=2,
        stage="Staging",
        archive_existing_versions=True,
    )


@patch("services.mlflow.registry.mlflow")
def test_load_production_model(mock_mlflow):
    mock_mlflow.sklearn.load_model.return_value = MagicMock()

    model = load_production_model("risk-classifier")

    mock_mlflow.sklearn.load_model.assert_called_once_with(
        "models:/risk-classifier/Production"
    )
    assert model is not None