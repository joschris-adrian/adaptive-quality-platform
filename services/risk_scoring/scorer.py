import yaml
from pathlib import Path
from services.risk_scoring.weights import load_weights

WEIGHTS_PATH = Path("services/risk_scoring/weights.yaml")


class RiskScorer:
    def __init__(self):
        self.weights = load_weights(WEIGHTS_PATH)

    def score(self, scored_event: dict) -> dict:
        likelihood  = self._compute_likelihood(scored_event)
        severity    = self._compute_severity(scored_event)
        exposure    = self._compute_exposure(scored_event)

        raw_score   = likelihood * severity * exposure
        normalized  = self._normalize(raw_score)
        priority    = self._assign_priority(normalized)

        return {
            "event_id":         scored_event["event_id"],
            "risk_score":       round(normalized, 4),
            "priority":         priority,
            "components": {
                "likelihood":   round(likelihood, 4),
                "severity":     round(severity, 4),
                "exposure":     round(exposure, 4),
            },
            "category":         scored_event["category"],
            "risk_metadata":    self._build_metadata(scored_event, priority),
        }

    def _compute_likelihood(self, event: dict) -> float:
        # Base: aggregated ML/rule/heuristic probability
        base = event.get("risk_probability", 0.0)

        # Boost if multiple detectors agree
        signals = event.get("signals", {})
        detector_scores = [
            signals.get("ml",        {}).get("risk_probability", 0.0),
            signals.get("rule",      {}).get("risk_probability", 0.0),
            signals.get("heuristic", {}).get("risk_probability", 0.0),
        ]
        agreement_bonus = 0.1 if all(s > 0.5 for s in detector_scores) else 0.0

        return min(base + agreement_bonus, 1.0)

    def _compute_severity(self, event: dict) -> float:
        category = event.get("category", "clean")
        severity_map = self.weights.get("severity", {})
        return severity_map.get(category, 0.2)

    def _compute_exposure(self, event: dict) -> float:
        source_event  = event.get("source_event", {})
        event_type    = source_event.get("event_type", "")
        source_system = source_event.get("source_system", "")

        exposure_map      = self.weights.get("exposure", {})
        event_type_score  = exposure_map.get("event_type",    {}).get(event_type,    0.3)
        source_sys_score  = exposure_map.get("source_system", {}).get(source_system, 0.3)

        return (event_type_score + source_sys_score) / 2.0

    def _normalize(self, raw: float) -> float:
        # Raw = likelihood * severity * exposure, max theoretical = 1.0
        # Clamp and apply a soft scaling to spread mid-range scores
        clamped = min(raw, 1.0)
        # Soft curve: pushes middling scores apart for better priority separation
        return clamped ** 0.75

    def _assign_priority(self, score: float) -> str:
        thresholds = self.weights.get("priority_thresholds", {})
        if score >= thresholds.get("critical", 0.85):
            return "critical"
        elif score >= thresholds.get("high", 0.65):
            return "high"
        elif score >= thresholds.get("medium", 0.40):
            return "medium"
        else:
            return "low"

    def _build_metadata(self, event: dict, priority: str) -> dict:
        rules_triggered = event.get("signals", {}).get("rule", {}).get("rules_triggered", [])
        heuristic_sigs  = event.get("signals", {}).get("heuristic", {}).get("signals", {})
        return {
            "rules_triggered":   rules_triggered,
            "heuristic_signals": heuristic_sigs,
            "requires_review":   priority in ("high", "critical"),
            "auto_actioned":     priority == "low",
        }