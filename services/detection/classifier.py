import joblib
import numpy as np
from pathlib import Path

MODEL_PATH = Path("models/classifier.pkl")
THRESHOLD  = 0.5

CATEGORY_MAP = {
    0: "clean",
    1: "policy_violation",
    2: "fraud",
    3: "spam",
    4: "abuse",
}

class MLClassifier:
    def __init__(self):
        self.model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

    def _extract_features(self, event: dict) -> np.ndarray:
        payload = event.get("payload", {})
        return np.array([
            payload.get("risk_hint", 0.0),
            len(str(payload)),
            1 if event.get("event_type") == "transaction" else 0,
            1 if event.get("source_system") == "api" else 0,
        ]).reshape(1, -1)

    async def detect(self, event: dict) -> dict:
        if self.model is None:
            # Fallback: use risk_hint from payload directly
            score = event.get("payload", {}).get("risk_hint", 0.0)
            label = 1 if score > THRESHOLD else 0
        else:
            features = self._extract_features(event)
            proba    = self.model.predict_proba(features)[0]
            label    = int(np.argmax(proba))
            score    = float(proba[label])

        return {
            "risk_probability": round(score, 4),
            "category":         CATEGORY_MAP.get(label, "unknown"),
            "detector":         "ml_classifier",
        }