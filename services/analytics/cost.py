from dataclasses import dataclass


@dataclass
class TierCostConfig:
    cost_per_event: float      # USD per reviewed event
    accuracy:       float      # probability of correct decision
    avg_review_minutes: float  # average time to review one event


TIER_COSTS = {
    "automated": TierCostConfig(cost_per_event=0.001, accuracy=0.72, avg_review_minutes=0.0),
    "standard":  TierCostConfig(cost_per_event=0.85,  accuracy=0.88, avg_review_minutes=4.5),
    "expert":    TierCostConfig(cost_per_event=3.20,  accuracy=0.97, avg_review_minutes=12.0),
}


class CostModel:
    def __init__(self, tier_costs: dict = None):
        self.tiers = tier_costs or TIER_COSTS

    def cost_for_event(self, tier: str) -> float:
        return self.tiers[tier].cost_per_event

    def accuracy_for_tier(self, tier: str) -> float:
        return self.tiers[tier].accuracy

    def compute_batch_cost(self, tier_counts: dict) -> dict:
        """
        tier_counts: {"automated": 800, "standard": 150, "expert": 50}
        Returns cost breakdown and totals.
        """
        total_events = sum(tier_counts.values())
        breakdown    = {}
        total_cost   = 0.0
        total_correct = 0.0

        for tier, count in tier_counts.items():
            cfg           = self.tiers[tier]
            cost          = count * cfg.cost_per_event
            correct       = count * cfg.accuracy
            total_cost   += cost
            total_correct += correct
            breakdown[tier] = {
                "count":          count,
                "cost":           round(cost, 4),
                "accuracy":       cfg.accuracy,
                "correct":        round(correct, 1),
                "minutes":        round(count * cfg.avg_review_minutes, 1),
                "pct_of_volume":  round(count / total_events * 100, 1) if total_events else 0,
            }

        system_accuracy = total_correct / total_events if total_events else 0.0

        return {
            "breakdown":       breakdown,
            "total_cost":      round(total_cost, 4),
            "total_events":    total_events,
            "system_accuracy": round(system_accuracy, 4),
            "cost_per_correct_decision": round(
                total_cost / total_correct if total_correct else 0, 4
            ),
        }