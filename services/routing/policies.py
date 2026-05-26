from dataclasses import dataclass, field


@dataclass
class RoutingPolicy:
    version: str = "1.0"

    # priority → default action
    priority_action_map: dict = field(default_factory=lambda: {
        "critical": "escalated_review",
        "high":     "escalated_review",
        "medium":   "standard_review",
        "low":      "auto_action",
    })

    # category overrides — always escalate these regardless of priority
    always_escalate_categories: set = field(default_factory=lambda: {
        "fraud",
        "policy_violation",
    })

    # score threshold below which we always auto-action
    auto_action_threshold: float = 0.25

    # score threshold above which we always escalate
    escalate_threshold: float = 0.80

    def resolve(self, priority: str, risk_score: float, category: str) -> str:
        # Hard override: very low score → always auto-action
        if risk_score < self.auto_action_threshold:
            return "auto_action"

        # Hard override: very high score → always escalate
        if risk_score >= self.escalate_threshold:
            return "escalated_review"

        # Category override: certain categories always get escalated
        if category in self.always_escalate_categories:
            return "escalated_review"

        # Default: resolve from priority map
        return self.priority_action_map.get(priority, "standard_review")


DEFAULT_POLICY = RoutingPolicy()