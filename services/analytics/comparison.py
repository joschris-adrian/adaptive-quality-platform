from services.analytics.cost    import CostModel,     TIER_COSTS
from services.analytics.quality import QualityTracker, QualityMetrics


# Pre-defined strategies for simulation and experimentation
STRATEGIES = {
    "automation_only": {
        "automated": 1.0,
        "standard":  0.0,
        "expert":    0.0,
    },
    "hybrid_balanced": {
        "automated": 0.70,
        "standard":  0.22,
        "expert":    0.08,
    },
    "hybrid_quality_first": {
        "automated": 0.40,
        "standard":  0.35,
        "expert":    0.25,
    },
    "human_heavy": {
        "automated": 0.10,
        "standard":  0.60,
        "expert":    0.30,
    },
}


class QualityCostComparator:
    def __init__(self, cost_model: CostModel = None):
        self.cost_model = cost_model or CostModel()

    def compare_strategies(
        self,
        total_events: int,
        strategies:   dict = None,
    ) -> dict:
        strategies = strategies or STRATEGIES
        results    = {}

        for name, split in strategies.items():
            tier_counts = {
                tier: int(total_events * pct)
                for tier, pct in split.items()
            }
            cost_report   = self.cost_model.compute_batch_cost(tier_counts)
            quality_score = self._estimate_quality(split)
            results[name] = {
                "tier_split":       split,
                "tier_counts":      tier_counts,
                "total_cost":       cost_report["total_cost"],
                "system_accuracy":  cost_report["system_accuracy"],
                "quality_score":    quality_score,
                "cost_per_correct": cost_report["cost_per_correct_decision"],
                "breakdown":        cost_report["breakdown"],
                "efficiency_ratio": self._efficiency_ratio(
                    quality_score, cost_report["total_cost"]
                ),
            }

        return {
            "total_events": total_events,
            "strategies":   results,
            "recommended":  self._recommend(results),
        }

    def threshold_sensitivity(
        self,
        total_events:    int,
        escalate_thresholds: list[float] = None,
    ) -> list[dict]:
        """
        Simulate how changing the escalation threshold shifts cost and quality.
        Lower threshold → more events escalated → higher cost, higher quality.
        """
        thresholds = escalate_thresholds or [0.5, 0.6, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
        results    = []

        for threshold in thresholds:
            # Approximate tier split from threshold
            expert_pct   = max(0.0, (1.0 - threshold))
            standard_pct = min(expert_pct * 0.6, 0.40)
            auto_pct     = max(0.0, 1.0 - expert_pct - standard_pct)

            split = {
                "automated": round(auto_pct,     3),
                "standard":  round(standard_pct, 3),
                "expert":    round(expert_pct,   3),
            }
            tier_counts  = {t: int(total_events * p) for t, p in split.items()}
            cost_report  = self.cost_model.compute_batch_cost(tier_counts)
            quality      = self._estimate_quality(split)

            results.append({
                "escalate_threshold": threshold,
                "tier_split":         split,
                "total_cost":         cost_report["total_cost"],
                "system_accuracy":    cost_report["system_accuracy"],
                "quality_score":      quality,
                "cost_per_correct":   cost_report["cost_per_correct_decision"],
            })

        return results

    def cost_under_budget(
        self,
        total_events:  int,
        budget:        float,
        strategies:    dict = None,
    ) -> list[dict]:
        """Return strategies that fit within a cost budget, ranked by quality."""
        strategies  = strategies or STRATEGIES
        comparison  = self.compare_strategies(total_events, strategies)
        affordable  = [
            {"name": name, **data}
            for name, data in comparison["strategies"].items()
            if data["total_cost"] <= budget
        ]
        return sorted(affordable, key=lambda x: x["quality_score"], reverse=True)

    def _estimate_quality(self, split: dict) -> float:
        """
        Weighted accuracy across tiers based on their proportion of volume.
        Uses tier accuracy from the cost model.
        """
        return sum(
            pct * self.cost_model.accuracy_for_tier(tier)
            for tier, pct in split.items()
        )

    def _efficiency_ratio(self, quality: float, cost: float) -> float:
        """Quality gained per dollar spent (higher = more efficient)."""
        return round(quality / cost if cost > 0 else 0.0, 6)

    def _recommend(self, results: dict) -> str:
        """
        Recommend the strategy with the best efficiency ratio
        that also achieves quality >= 0.80.
        """
        qualified = {
            name: data for name, data in results.items()
            if data["quality_score"] >= 0.80
        }
        if not qualified:
            # Fallback: highest quality regardless of cost
            return max(results, key=lambda n: results[n]["quality_score"])

        return max(qualified, key=lambda n: qualified[n]["efficiency_ratio"])