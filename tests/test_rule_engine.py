import pytest
from services.detection.rules import RuleEngine, BLOCKLISTED_USERS


@pytest.fixture
def engine():
    return RuleEngine()


def _make_event(risk_hint=0.0, user_id="u1", source_system="web",
                event_type="user_action", category="normal"):
    return {
        "event_id":    "evt-rule",
        "event_type":  event_type,
        "source_system": source_system,
        "payload": {"user_id": user_id, "risk_hint": risk_hint, "category": category},
        "timestamp": "2026-01-01T00:00:00",
    }


@pytest.mark.asyncio
async def test_no_rules_triggered_returns_clean(engine):
    result = await engine.detect(_make_event(risk_hint=0.1))
    assert result["category"]         == "clean"
    assert result["risk_probability"] == 0.0
    assert result["rules_triggered"]  == []


@pytest.mark.asyncio
async def test_high_risk_hint_triggers(engine):
    result = await engine.detect(_make_event(risk_hint=0.95))
    assert "high_risk_hint"   in result["rules_triggered"]
    assert result["risk_probability"] >= 0.9


@pytest.mark.asyncio
async def test_blocklisted_user_triggers(engine):
    blocked = next(iter(BLOCKLISTED_USERS))
    result  = await engine.detect(_make_event(user_id=blocked))
    assert "blocklisted_user"         in result["rules_triggered"]
    assert result["risk_probability"] == 1.0
    assert result["category"]         == "fraud"


@pytest.mark.asyncio
async def test_suspicious_api_source_triggers(engine):
    result = await engine.detect(_make_event(risk_hint=0.65, source_system="api"))
    assert "suspicious_api_source" in result["rules_triggered"]


@pytest.mark.asyncio
async def test_known_bad_category_triggers(engine):
    result = await engine.detect(_make_event(category="fraud"))
    assert "known_bad_category"       in result["rules_triggered"]
    assert result["category"]         == "fraud"


@pytest.mark.asyncio
async def test_multiple_rules_returns_highest_score(engine):
    blocked = next(iter(BLOCKLISTED_USERS))
    # blocklisted_user (1.0) + high_risk_hint (0.95) — should return 1.0
    result = await engine.detect(_make_event(risk_hint=0.95, user_id=blocked))
    assert result["risk_probability"] == 1.0
    assert len(result["rules_triggered"]) >= 2


@pytest.mark.asyncio
async def test_api_below_threshold_does_not_trigger(engine):
    result = await engine.detect(_make_event(risk_hint=0.55, source_system="api"))
    assert "suspicious_api_source" not in result["rules_triggered"]