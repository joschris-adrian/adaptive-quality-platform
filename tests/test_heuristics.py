import pytest
from datetime import datetime, timezone, timedelta
from services.detection.heuristics import HeuristicDetector


@pytest.fixture
def detector():
    return HeuristicDetector()


def _event(payload_text="", event_type="user_action", timestamp=None):
    ts = timestamp or datetime.now(timezone.utc).isoformat()
    return {
        "event_id":    "evt-heur",
        "event_type":  event_type,
        "source_system": "web",
        "payload": {"content": payload_text, "risk_hint": 0.1},
        "timestamp": ts,
    }


@pytest.mark.asyncio
async def test_clean_event_returns_low_score(detector):
    result = await detector.detect(_event("hello world"))
    assert result["risk_probability"] < 0.3
    assert result["category"] == "clean"


@pytest.mark.asyncio
async def test_spam_pattern_detected(detector):
    result = await detector.detect(_event("click here to buy now limited offer"))
    assert result["signals"]["spam_patterns"] > 0
    assert result["category"] == "spam"


@pytest.mark.asyncio
async def test_url_in_payload_triggers_spam(detector):
    result = await detector.detect(_event("visit https://suspicious.biz/offer"))
    assert result["signals"]["spam_patterns"] > 0


@pytest.mark.asyncio
async def test_stale_timestamp_triggers_time_anomaly(detector):
    stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    result   = await detector.detect(_event(timestamp=stale_ts))
    assert result["signals"]["time_anomaly"] > 0


@pytest.mark.asyncio
async def test_fresh_timestamp_no_time_anomaly(detector):
    result = await detector.detect(_event())
    assert result["signals"]["time_anomaly"] == 0.0


@pytest.mark.asyncio
async def test_invalid_timestamp_does_not_crash(detector):
    event = _event()
    event["timestamp"] = "not-a-date"
    result = await detector.detect(event)
    assert result["signals"]["time_anomaly"] == 0.0


@pytest.mark.asyncio
async def test_user_action_gets_velocity_score(detector):
    result = await detector.detect(_event(event_type="user_action"))
    assert result["signals"]["velocity"] == 0.3


@pytest.mark.asyncio
async def test_non_user_action_zero_velocity(detector):
    result = await detector.detect(_event(event_type="transaction"))
    assert result["signals"]["velocity"] == 0.0


@pytest.mark.asyncio
async def test_spam_score_capped_at_one(detector):
    # Many spam signals should not push spam_patterns above 1.0
    text   = "click here buy now limited offer act fast click here buy now"
    result = await detector.detect(_event(text))
    assert result["signals"]["spam_patterns"] <= 1.0