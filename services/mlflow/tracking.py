import mlflow
import os

TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
mlflow.set_tracking_uri(TRACKING_URI)


def log_experiment_run(experiment_name: str, run_name: str, params: dict, metrics: dict, tags: dict = None):
    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name):
        mlflow.log_params(params)
        mlflow.log_metrics(metrics)
        if tags:
            mlflow.set_tags(tags)


def log_threshold_sweep(threshold: float, results: dict):
    log_experiment_run(
        experiment_name="threshold-sweep",
        run_name=f"threshold_{threshold}",
        params={"threshold": threshold},
        metrics={
            "quality": results.get("quality", 0),
            "cost": results.get("cost", 0),
            "auto_pct": results.get("auto_pct", 0),
        },
    )


def log_drift_snapshot(report: dict):
    log_experiment_run(
        experiment_name="drift-monitoring",
        run_name="drift_snapshot",
        params={},
        metrics={
            "precision_delta": report.get("precision_delta", 0),
            "recall_delta": report.get("recall_delta", 0),
            "emerging_categories_count": len(report.get("emerging_categories", [])),
        },
        tags={"status": report.get("status", "unknown")},
    )


def log_ab_variant(experiment_name: str, variant: str, params: dict, metrics: dict):
    log_experiment_run(
        experiment_name=experiment_name,
        run_name=f"variant_{variant}",
        params={"variant": variant, **params},
        metrics=metrics,
    )