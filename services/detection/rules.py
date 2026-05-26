import re

BLOCKLISTED_USERS = {"banned_user_1", "banned_user_2"}
HIGH_RISK_CATEGORIES = {"fraud", "policy_violation"}

RULES = [
    {
        "name":     "high_risk_hint",
        "check":    lambda e: e.get("payload", {}).get("risk_hint", 0) >= 0.9,
        "score":    0.95,
        "category": "policy_violation",
    },
    {
        "name":     "blocklisted_user",
        "check":    lambda e: e.get("payload", {}).get("user_id") in BLOCKLISTED_USERS,
        "score":    1.0,
        "category": "fraud",
    },
    {
        "name":     "suspicious_api_source",
        "check":    lambda e: (
            e.get("source_system") == "api"
            and e.get("payload", {}).get("risk_hint", 0) > 0.6
        ),
        "score":    0.75,
        "category": "abuse",
    },
    {
        "name":     "known_bad_category",
        "check":    lambda e: e.get("payload", {}).get("category") in HIGH_RISK_CATEGORIES,
        "score":    0.8,
        "category": e["payload"].get("category") if (e := {}) else "policy_violation",
        # Note: use a method-based approach below for dynamic category
    },
]

class RuleEngine:
    def __init__(self, rules: list = None):
        self.rules = rules or self._default_rules()

    def _default_rules(self):
        return [
            self._high_risk_hint_rule,
            self._blocklisted_user_rule,
            self._suspicious_api_rule,
            self._known_bad_category_rule,
        ]

    def _high_risk_hint_rule(self, event):
        if event.get("payload", {}).get("risk_hint", 0) >= 0.9:
            return {"score": 0.95, "category": "policy_violation", "rule": "high_risk_hint"}

    def _blocklisted_user_rule(self, event):
        if event.get("payload", {}).get("user_id") in BLOCKLISTED_USERS:
            return {"score": 1.0, "category": "fraud", "rule": "blocklisted_user"}

    def _suspicious_api_rule(self, event):
        if event.get("source_system") == "api" and event.get("payload", {}).get("risk_hint", 0) > 0.6:
            return {"score": 0.75, "category": "abuse", "rule": "suspicious_api_source"}

    def _known_bad_category_rule(self, event):
        cat = event.get("payload", {}).get("category")
        if cat in HIGH_RISK_CATEGORIES:
            return {"score": 0.8, "category": cat, "rule": "known_bad_category"}

    async def detect(self, event: dict) -> dict:
        triggered = []
        for rule_fn in self.rules:
            result = rule_fn(event)
            if result:
                triggered.append(result)

        if not triggered:
            return {"risk_probability": 0.0, "category": "clean", "detector": "rule_engine", "rules_triggered": []}

        # Take the highest scoring triggered rule
        top = max(triggered, key=lambda r: r["score"])
        return {
            "risk_probability": top["score"],
            "category":         top["category"],
            "detector":         "rule_engine",
            "rules_triggered":  [r["rule"] for r in triggered],
        }