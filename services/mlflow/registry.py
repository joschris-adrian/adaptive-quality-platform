import mlflow
from mlflow.tracking import MlflowClient


def register_model(run_id: str, model_name: str, artifact_path: str = "model"):
    model_uri = f"runs:/{run_id}/{artifact_path}"
    mlflow.register_model(model_uri, model_name)


def promote_model(model_name: str, version: int, stage: str = "Production"):
    client = MlflowClient()
    client.transition_model_version_stage(
        name=model_name,
        version=version,
        stage=stage,
        archive_existing_versions=True,
    )


def load_production_model(model_name: str):
    return mlflow.sklearn.load_model(f"models:/{model_name}/Production")