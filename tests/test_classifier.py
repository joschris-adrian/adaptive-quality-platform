import pytest
import numpy as np
from unittest.mock import MagicMock, patch
from services.detection.classifier import MLClassifier


@pytest.fixture
def event_high_risk():
    return {
        "event_id":    "evt-002",
        "event_type":  "transaction",
        "source_system": "api",
        "payload": {"user_id": "u1", "risk_hint": 0.95, "category": "fraud"},
        "timestamp": "2026-01-01T00:00:00",
    }


@pytest.fixture
def event_low_risk():
    return {
        "event_id":    "evt-003",
        "event_type":  "user_action",
        "source_system": "web",
        "payload": {"user_id": "u2", "risk_hint": 0.1, "category": "normal"},
        "timestamp": "2026-01-01T00:00:00",
    }


@pytest.mark.asyncio
async def test_classifier_fallback_high_risk(event_high_risk):
    clf = MLClassifier()
    clf.model = None   # force fallback path

    result = await clf.detect(event_high_risk)

    assert result["risk_probability"] > 0.5
    assert result["detector"] == "ml_classifier"


@pytest.mark.asyncio
async def test_classifier_fallback_low_risk(event_low_risk):
    clf = MLClassifier()
    clf.model = None

    result = await clf.detect(event_low_risk)

    assert result["risk_probability"] < 0.5
    assert result["category"] == "clean"


@pytest.mark.asyncio
async def test_classifier_uses_model_when_present(event_high_risk):
    clf = MLClassifier()
    mock_model = MagicMock()
    mock_model.predict_proba.return_value = np.array([[0.05, 0.90, 0.03, 0.01, 0.01]])
    clf.model = mock_model

    result = await clf.detect(event_high_risk)

    assert result["risk_probability"] == pytest.approx(0.90, abs=1e-4)
    assert result["category"] == "policy_violation"


def test_feature_extraction_shape(event_high_risk):
    clf      = MLClassifier()
    features = clf._extract_features(event_high_risk)

    assert features.shape == (1, 4)


def test_feature_extraction_transaction_flag(event_high_risk):
    clf      = MLClassifier()
    features = clf._extract_features(event_high_risk)

    # index 2 = is_transaction, index 3 = is_api
    assert features[0][2] == 1.0
    assert features[0][3] == 1.0


def test_feature_extraction_non_transaction():
    clf   = MLClassifier()
    event = {
        "event_type": "user_action", "source_system": "web",
        "payload": {"risk_hint": 0.2},
    }
    features = clf._extract_features(event)
    assert features[0][2] == 0.0
    assert features[0][3] == 0.0