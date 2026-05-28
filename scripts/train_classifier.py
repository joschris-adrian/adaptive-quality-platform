import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import mlflow
import mlflow.sklearn
import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_score, recall_score, f1_score
from sklearn.model_selection import train_test_split
from services.mlflow.registry import register_model, promote_model

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--wandb", action="store_true", help="Log to Weights & Biases")
args = parser.parse_args()

mlflow.set_tracking_uri("http://localhost:5000")
mlflow.set_experiment("classifier-training")

# Replace with real data loading when available
np.random.seed(42)
X = np.random.rand(1000, 5)
y = (X[:, 0] + X[:, 1] > 1.0).astype(int)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

params = {"C": 1.0, "max_iter": 200, "solver": "lbfgs"}

with mlflow.start_run(run_name="logistic_regression") as run:
    model = LogisticRegression(**params)
    model.fit(X_train, y_train)
    preds = model.predict(X_test)

    precision = precision_score(y_test, preds)
    recall = recall_score(y_test, preds)
    f1 = f1_score(y_test, preds)

    mlflow.log_params(params)
    mlflow.log_metrics({"precision": precision, "recall": recall, "f1": f1})
    mlflow.sklearn.log_model(model, artifact_path="model")

    print(f"Precision: {precision:.3f} | Recall: {recall:.3f} | F1: {f1:.3f}")
    print(f"Run ID: {run.info.run_id}")

    register_model(run_id=run.info.run_id, model_name="risk-classifier")
    promote_model(model_name="risk-classifier", version=1, stage="Production")
    print("Model registered and promoted to Production.")

# W&B logging (optional — runs only if wandb is configured)
if args.wandb:
    try:
        from services.wandb.tracker import init_run, log_metrics as wb_log, log_table, finish
        init_run(project="risk-classifier", run_name="logistic_regression", config=params)
        wb_log({"precision": precision, "recall": recall, "f1": f1})
        fp_rows = [[i, float(X_test[i][0])] for i in range(len(preds)) if preds[i] == 1 and y_test[i] == 0]
        fn_rows = [[i, float(X_test[i][0])] for i in range(len(preds)) if preds[i] == 0 and y_test[i] == 1]
        log_table("false_positives", ["index", "feature_0"], fp_rows)
        log_table("false_negatives", ["index", "feature_0"], fn_rows)
        finish()
    except Exception:
        pass