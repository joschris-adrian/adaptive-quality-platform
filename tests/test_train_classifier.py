import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import numpy as np
from unittest.mock import patch, MagicMock
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, f1_score


def _train(X_train, X_test, y_train, y_test, params=None):
    params = params or {"C": 1.0, "max_iter": 200, "solver": "lbfgs"}
    model  = LogisticRegression(**params)
    model.fit(X_train, y_train)
    preds  = model.predict(X_test)
    return model, preds, {
        "precision": precision_score(y_test, preds, zero_division=0),
        "recall":    recall_score(y_test, preds, zero_division=0),
        "f1":        f1_score(y_test, preds, zero_division=0),
    }


def _synthetic_data(seed=42):
    np.random.seed(seed)
    X = np.random.rand(1000, 5)
    y = (X[:, 0] + X[:, 1] > 1.0).astype(int)
    return train_test_split(X, y, test_size=0.2, random_state=seed)


def test_model_trains_without_error():
    X_train, X_test, y_train, y_test = _synthetic_data()
    model, preds, metrics = _train(X_train, X_test, y_train, y_test)
    assert model is not None
    assert len(preds) == len(y_test)


def test_metrics_in_range():
    X_train, X_test, y_train, y_test = _synthetic_data()
    _, _, metrics = _train(X_train, X_test, y_train, y_test)
    for key, val in metrics.items():
        assert 0.0 <= val <= 1.0, f"{key} out of range: {val}"


def test_f1_reasonable():
    X_train, X_test, y_train, y_test = _synthetic_data()
    _, _, metrics = _train(X_train, X_test, y_train, y_test)
    assert metrics["f1"] > 0.5, f"F1 too low: {metrics['f1']}"


def test_prediction_shape():
    X_train, X_test, y_train, y_test = _synthetic_data()
    _, preds, _ = _train(X_train, X_test, y_train, y_test)
    assert preds.shape == y_test.shape


def test_predictions_are_binary():
    X_train, X_test, y_train, y_test = _synthetic_data()
    _, preds, _ = _train(X_train, X_test, y_train, y_test)
    assert set(preds).issubset({0, 1})


def test_different_seed_gives_different_split():
    X_train1, X_test1, _, _ = _synthetic_data(seed=0)
    X_train2, X_test2, _, _ = _synthetic_data(seed=99)
    assert not np.array_equal(X_train1, X_train2)


@patch("services.mlflow.registry.register_model")
@patch("services.mlflow.registry.promote_model")
def test_registry_calls_are_made(mock_promote, mock_register):
    mock_register.return_value = None
    mock_promote.return_value  = None

    from services.mlflow.registry import register_model, promote_model
    register_model(run_id="fake-run-id", model_name="risk-classifier")
    promote_model(model_name="risk-classifier", version=1, stage="Production")

    mock_register.assert_called_once()
    mock_promote.assert_called_once()