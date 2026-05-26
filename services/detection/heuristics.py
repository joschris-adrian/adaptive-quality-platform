import re
from datetime import datetime, timezone

SPAM_PATTERNS = [
    re.compile(r"\b(click here|buy now|limited offer|act fast)\b", re.IGNORECASE),
    re.compile(r"https?://\S+\.\S{2,}"),   # raw URLs in payload strings
]

class HeuristicDetector:
    def _payload_text(self, event: dict) -> str:
        return " ".join(str(v) for v in event.get("payload", {}).values())

    def _velocity_check(self, event: dict) -> float:
        # Placeholder: in production, query a Redis sliding window counter
        # Returns a synthetic score based on event type frequency hint
        return 0.3 if event.get("event_type") == "user_action" else 0.0

    def _spam_pattern_check(self, text: str) -> float:
        matches = sum(1 for p in SPAM_PATTERNS if p.search(text))
        return min(matches * 0.35, 1.0)

    def _time_anomaly_check(self, event: dict) -> float:
        # Flag events arriving with a stale timestamp (>5 min old)
        try:
            ts = datetime.fromisoformat(event.get("timestamp", ""))
            age_seconds = (datetime.now(timezone.utc) - ts.replace(tzinfo=timezone.utc)).total_seconds()
            return 0.6 if age_seconds > 300 else 0.0
        except Exception:
            return 0.0

    async def detect(self, event: dict) -> dict:
        text = self._payload_text(event)

        signal_scores = {
            "velocity":      self._velocity_check(event),
            "spam_patterns": self._spam_pattern_check(text),
            "time_anomaly":  self._time_anomaly_check(event),
        }

        # Weighted combination of signals
        final = (
            signal_scores["velocity"]      * 0.3 +
            signal_scores["spam_patterns"] * 0.5 +
            signal_scores["time_anomaly"]  * 0.2
        )

        category = "spam" if signal_scores["spam_patterns"] > 0 else \
                   "anomaly" if signal_scores["time_anomaly"] > 0 else "clean"

        return {
            "risk_probability": round(final, 4),
            "category":         category,
            "detector":         "heuristics",
            "signals":          signal_scores,
        }