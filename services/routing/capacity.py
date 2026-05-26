import logging

logger = logging.getLogger(__name__)

# In production these come from Redis or a workforce management API.
# Here they are in-memory defaults for local dev and testing.
DEFAULT_CAPACITY = {
    "standard": {"limit": 500, "current": 0},
    "expert":   {"limit": 100, "current": 0},
}

DOWNGRADE_MAP = {
    "escalated_review": "standard_review",
    "standard_review":  "auto_action",
}


class CapacityManager:
    def __init__(self, capacity: dict = None):
        self.capacity = capacity or {
            k: dict(v) for k, v in DEFAULT_CAPACITY.items()
        }

    def is_available(self, tier: str) -> bool:
        if tier == "automated":
            return True
        info = self.capacity.get(tier)
        if not info:
            return True
        return info["current"] < info["limit"]

    def adjust(self, action: str, priority: str) -> str:
        tier = self._action_to_tier(action)

        if self.is_available(tier):
            return action

        # Critical events are never downgraded — hold for capacity
        if priority == "critical":
            logger.warning(f"Critical event held — {tier} queue at capacity")
            return "hold"

        downgraded = DOWNGRADE_MAP.get(action)
        if downgraded:
            logger.info(f"Downgrading {action} → {downgraded} due to capacity")
            return downgraded

        return action

    def increment(self, tier: str):
        if tier in self.capacity:
            self.capacity[tier]["current"] += 1

    def decrement(self, tier: str):
        if tier in self.capacity:
            self.capacity[tier]["current"] = max(
                0, self.capacity[tier]["current"] - 1
            )

    def _action_to_tier(self, action: str) -> str:
        return {
            "escalated_review": "expert",
            "hold":             "expert",
            "standard_review":  "standard",
            "auto_action":      "automated",
        }.get(action, "standard")

    def snapshot(self) -> dict:
        return {
            tier: {
                "limit":     info["limit"],
                "current":   info["current"],
                "available": info["limit"] - info["current"],
                "pct_full":  round(info["current"] / info["limit"] * 100, 1),
            }
            for tier, info in self.capacity.items()
        }