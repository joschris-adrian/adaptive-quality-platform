import asyncio
from services.detection.classifier import MLClassifier
from services.detection.rules import RuleEngine
from services.detection.heuristics import HeuristicDetector

class DetectionPipeline:
    def __init__(self):
        self.classifier  = MLClassifier()
        self.rule_engine = RuleEngine()
        self.heuristics  = HeuristicDetector()

    async def run(self, event: dict) -> dict:
        ml_result, rule_result, heuristic_result = await asyncio.gather(
            self.classifier.detect(event),
            self.rule_engine.detect(event),
            self.heuristics.detect(event),
        )
        return self._aggregate(event, ml_result, rule_result, heuristic_result)

    def _aggregate(self, event, ml, rule, heuristic) -> dict:
        scores = [
            ml["risk_probability"] * 0.5,
            rule["risk_probability"] * 0.3,
            heuristic["risk_probability"] * 0.2,
        ]
        final_score = sum(scores)

        category = ml["category"]
        if rule["category"] != "clean":
            category = rule["category"]
        if heuristic["category"] != "clean":
            category = heuristic["category"]

        return {
            "event_id":         event["event_id"],
            "risk_probability": round(final_score, 4),
            "category":         category,
            "signals": {
                "ml":        ml,
                "rule":      rule,
                "heuristic": heuristic,
            },
            "source_event": event,
        }