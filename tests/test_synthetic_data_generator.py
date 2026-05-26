import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.synthetic_data_generator import generate_event


VALID_EVENT_TYPES = {
    "user_action", "moderation_decision",
    "transaction", "review_outcome", "operational_alert"
}
VALID_SOURCE_SYSTEMS = {"web", "mobile", "api"}
VALID_CATEGORIES     = {"spam", "fraud", "policy_violation", "normal"}


# ── generate_event ─────────────────────────────────────────────────────────

def test_generate_event_returns_dict():
    assert isinstance(generate_event(), dict)


def test_generate_event_has_required_keys():
    e = generate_event()
    for key in ["event_type", "source_system", "payload", "timestamp"]:
        assert key in e


def test_generate_event_type_is_valid():
    for _ in range(20):
        assert generate_event()["event_type"] in VALID_EVENT_TYPES


def test_generate_event_source_system_is_valid():
    for _ in range(20):
        assert generate_event()["source_system"] in VALID_SOURCE_SYSTEMS


def test_generate_event_payload_has_user_id():
    e = generate_event()
    assert "user_id" in e["payload"]


def test_generate_event_payload_has_risk_hint():
    e = generate_event()
    assert "risk_hint" in e["payload"]


def test_generate_event_risk_hint_in_range():
    for _ in range(20):
        hint = generate_event()["payload"]["risk_hint"]
        assert 0.0 <= hint <= 1.0


def test_generate_event_payload_has_category():
    e = generate_event()
    assert "category" in e["payload"]


def test_generate_event_category_is_valid():
    for _ in range(20):
        cat = generate_event()["payload"]["category"]
        assert cat in VALID_CATEGORIES


def test_generate_event_timestamp_is_string():
    e = generate_event()
    assert isinstance(e["timestamp"], str)


def test_generate_event_timestamp_not_empty():
    e = generate_event()
    assert len(e["timestamp"]) > 0


def test_generate_event_transaction_has_amount():
    # run many times to hit a transaction event
    found_transaction = False
    for _ in range(200):
        e = generate_event()
        if e["event_type"] == "transaction":
            found_transaction = True
            assert "amount" in e["payload"], \
                "transaction event missing amount"
            assert e["payload"]["amount"] > 0
    assert found_transaction, "No transaction event generated in 200 tries"


def test_generate_event_amount_in_range():
    for _ in range(200):
        e = generate_event()
        if e["event_type"] == "transaction":
            assert 10.0 <= e["payload"]["amount"] <= 50_000.0


def test_generate_event_produces_variety():
    types = {generate_event()["event_type"] for _ in range(100)}
    assert len(types) >= 3


def test_generate_event_each_call_independent():
    e1 = generate_event()
    e2 = generate_event()
    # user_ids should differ across calls
    assert e1["payload"]["user_id"] != e2["payload"]["user_id"]