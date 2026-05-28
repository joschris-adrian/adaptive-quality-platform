import os


def _wandb():
    import wandb
    return wandb


def init_run(project: str, run_name: str, config: dict = None):
    wandb = _wandb()
    wandb.init(
        project=project,
        name=run_name,
        config=config or {},
        reinit=True,
    )


def log_metrics(metrics: dict):
    _wandb().log(metrics)


def log_model(model, model_name: str, metadata: dict = None):
    wandb = _wandb()
    artifact = wandb.Artifact(model_name, type="model", metadata=metadata or {})
    wandb.log_artifact(artifact)


def finish():
    _wandb().finish()


def log_table(name: str, columns: list, rows: list):
    wandb = _wandb()
    table = wandb.Table(columns=columns, data=rows)
    wandb.log({name: table})