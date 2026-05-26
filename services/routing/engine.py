from services.routing.policies import RoutingPolicy, DEFAULT_POLICY
from services.routing.capacity import CapacityManager


class RoutingEngine:
    def __init__(self, policy: RoutingPolicy = None, capacity: CapacityManager = None):
        self.policy   = policy   or DEFAULT_POLICY
        self.capacity = capacity or CapacityManager()

    def route(self, risk_event: dict) -> dict:
        priority   = risk_event["priority"]
        risk_score = risk_event["risk_score"]
        category   = risk_event["category"]

        # Determine base action from policy
        action     = self.policy.resolve(priority, risk_score, category)

        # Capacity check — downgrade if human queues are saturated
        action     = self.capacity.adjust(action, priority)

        tier       = self._assign_tier(action, priority)
        queue      = self._assign_queue(tier, category)
        sla_minutes = self._assign_sla(tier)

        return {
            "event_id":    risk_event["event_id"],
            "action":      action,
            "tier":        tier,
            "queue":       queue,
            "sla_minutes": sla_minutes,
            "priority":    priority,
            "risk_score":  risk_score,
            "category":    category,
            "requires_human": action != "auto_action",
            "routing_metadata": self._build_metadata(risk_event, action, tier),
        }

    def _assign_tier(self, action: str, priority: str) -> str:
        return {
            "auto_action":      "automated",
            "standard_review":  "standard",
            "escalated_review": "expert",
            "hold":             "expert",
        }.get(action, "standard")

    def _assign_queue(self, tier: str, category: str) -> str:
        if tier == "automated":
            return "auto-actioned-events"
        if tier == "expert":
            return f"expert-review-{category}"
        return f"standard-review-{category}"

    def _assign_sla(self, tier: str) -> int:
        return {
            "automated": 0,
            "standard":  60,
            "expert":    15,
        }.get(tier, 60)

    def _build_metadata(self, event: dict, action: str, tier: str) -> dict:
        return {
            "rules_triggered":   event.get("risk_metadata", {}).get("rules_triggered", []),
            "heuristic_signals": event.get("risk_metadata", {}).get("heuristic_signals", {}),
            "components":        event.get("components", {}),
            "policy_version":    self.policy.version,
            "capacity_available": self.capacity.is_available(tier),
        }