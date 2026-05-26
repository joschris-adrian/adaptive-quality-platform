import pytest
from services.routing.engine import RoutingEngine
from services.routing.policies import RoutingPolicy
from services.routing.capacity import CapacityManager


def _risk_event(
    priority="high",
    risk_score=0.75,
    category="fraud",
    rules_triggered=None,
):
    return {
        "event_id":   "evt-route-001",
        "priority":   priority,
        "risk_score": risk_score,
        "category":   category,
        "components": {"likelihood": 0.9, "severity": 1.0, "exposure": 0.85},
        "risk_metadata": {
            "rules_triggered":   rules_triggered or ["blocklisted_user"],
            "heuristic_signals": {"spam_patterns": 0.5},
            "requires_review":   True,
            "auto_actioned":     False,
        },
    }


@pytest.fixture
def engine():
    return RoutingEngine()


# --- Policy resolution ---

def test_low_priority_auto_actioned(engine):
    result = engine.route(_risk_event(priority="low", risk_score=0.2, category="clean"))
    assert result["action"] == "auto_action"
    assert result["requires_human"] is False


def test_medium_priority_standard_review(engine):
    result = engine.route(_risk_event(priority="medium", risk_score=0.50, category="spam"))
    assert result["action"] == "standard_review"
    assert result["tier"]   == "standard"


def test_high_priority_escalated_review(engine):
    result = engine.route(_risk_event(priority="high", risk_score=0.75, category="abuse"))
    assert result["action"] == "escalated_review"
    assert result["tier"]   == "expert"


def test_critical_priority_escalated_review(engine):
    result = engine.route(_risk_event(priority="critical", risk_score=0.92, category="fraud"))
    assert result["action"] == "escalated_review"


# --- Score threshold overrides ---

def test_score_below_auto_threshold_always_auto_actioned(engine):
    # Even medium priority should auto-action if score is very low
    result = engine.route(_risk_event(priority="medium", risk_score=0.10, category="spam"))
    assert result["action"] == "auto_action"


def test_score_above_escalate_threshold_always_escalated(engine):
    # Even low priority should escalate if score is very high
    result = engine.route(_risk_event(priority="low", risk_score=0.95, category="clean"))
    assert result["action"] == "escalated_review"


# --- Category overrides ---

def test_fraud_category_always_escalated(engine):
    result = engine.route(_risk_event(priority="medium", risk_score=0.50, category="fraud"))
    assert result["action"] == "escalated_review"


def test_policy_violation_always_escalated(engine):
    result = engine.route(_risk_event(priority="medium", risk_score=0.50, category="policy_violation"))
    assert result["action"] == "escalated_review"


def test_spam_category_not_force_escalated(engine):
    result = engine.route(_risk_event(priority="medium", risk_score=0.50, category="spam"))
    assert result["action"] == "standard_review"


# --- Queue and SLA assignment ---

def test_auto_action_goes_to_auto_queue(engine):
    result = engine.route(_risk_event(priority="low", risk_score=0.2, category="clean"))
    assert result["queue"] == "auto-actioned-events"


def test_standard_review_queue_contains_category(engine):
    result = engine.route(_risk_event(priority="medium", risk_score=0.50, category="spam"))
    assert result["queue"] == "standard-review-spam"


def test_expert_review_queue_contains_category(engine):
    result = engine.route(_risk_event(priority="high", risk_score=0.75, category="abuse"))
    assert result["queue"] == "expert-review-abuse"


def test_automated_tier_zero_sla(engine):
    result = engine.route(_risk_event(priority="low", risk_score=0.2, category="clean"))
    assert result["sla_minutes"] == 0


def test_standard_tier_sixty_min_sla(engine):
    result = engine.route(_risk_event(priority="medium", risk_score=0.50, category="spam"))
    assert result["sla_minutes"] == 60


def test_expert_tier_fifteen_min_sla(engine):
    result = engine.route(_risk_event(priority="high", risk_score=0.75, category="abuse"))
    assert result["sla_minutes"] == 15


# --- Capacity management ---

def test_saturated_standard_queue_downgrades_to_auto(engine):
    engine.capacity.capacity["standard"]["current"] = 500   # at limit
    result = engine.route(_risk_event(priority="medium", risk_score=0.50, category="spam"))
    assert result["action"] == "auto_action"


def test_saturated_expert_queue_downgrades_to_standard(engine):
    engine.capacity.capacity["expert"]["current"] = 100   # at limit
    result = engine.route(_risk_event(priority="high", risk_score=0.75, category="abuse"))
    assert result["action"] == "standard_review"


def test_critical_event_held_when_expert_saturated(engine):
    engine.capacity.capacity["expert"]["current"] = 100
    result = engine.route(_risk_event(priority="critical", risk_score=0.92, category="fraud"))
    assert result["action"] == "hold"
    assert result["tier"]   == "expert"


def test_capacity_snapshot_structure():
    cm       = CapacityManager()
    snapshot = cm.snapshot()
    assert "standard" in snapshot
    assert "expert"   in snapshot
    for tier in snapshot.values():
        assert "limit"     in tier
        assert "current"   in tier
        assert "available" in tier
        assert "pct_full"  in tier


def test_capacity_increment_decrement():
    cm = CapacityManager()
    cm.increment("standard")
    assert cm.capacity["standard"]["current"] == 1
    cm.decrement("standard")
    assert cm.capacity["standard"]["current"] == 0


def test_capacity_decrement_does_not_go_negative():
    cm = CapacityManager()
    cm.decrement("standard")
    assert cm.capacity["standard"]["current"] == 0


# --- Output schema ---

def test_routed_event_has_all_fields(engine):
    result = engine.route(_risk_event())
    for field in [
        "event_id", "action", "tier", "queue",
        "sla_minutes", "priority", "risk_score",
        "category", "requires_human", "routing_metadata",
    ]:
        assert field in result


def test_routing_metadata_has_policy_version(engine):
    result = engine.route(_risk_event())
    assert "policy_version" in result["routing_metadata"]
    assert result["routing_metadata"]["policy_version"] == "1.0"


# --- Custom policy ---

def test_custom_policy_changes_auto_threshold():
    policy = RoutingPolicy(auto_action_threshold=0.5)
    engine = RoutingEngine(policy=policy)
    # score=0.45 would normally be medium/standard, but now below auto threshold
    result = engine.route(_risk_event(priority="medium", risk_score=0.45, category="spam"))
    assert result["action"] == "auto_action"


def test_custom_policy_version_propagates():
    policy = RoutingPolicy(version="2.0")
    engine = RoutingEngine(policy=policy)
    result = engine.route(_risk_event())
    assert result["routing_metadata"]["policy_version"] == "2.0"