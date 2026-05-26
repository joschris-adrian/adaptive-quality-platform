import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from api.main import app
from api.routes.ingest import validate, enrich
from api.schemas import IncomingEvent

client = TestClient(app)


def _event(**kwargs):
    base = {
        "event_type":    "user_action",
        "source_system": "web",
        "payload":       {"user_id": "u1", "risk_hint": 0.5, "category": "normal"},
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }
    base.update(kwargs)
    return base


def _incoming(**kwargs):
    return IncomingEvent(**_event(**kwargs))


def _mock_producer():
    mock = MagicMock()
    mock.send.return_value         = MagicMock()
    mock.partitions_for.return_value = {0, 1, 2}
    return mock


# ── schema validation ──────────────────────────────────────────────────────

def test_valid_event_accepted():
    with patch("api.routes.ingest.get_producer", return_value=_mock_producer()):
        r = client.post("/api/v1/ingest", json=_event())
    assert r.status_code == 202


def test_invalid_event_type_rejected():
    r = client.post("/api/v1/ingest", json=_event(event_type="unknown_type"))
    assert r.status_code == 422


def test_blank_source_system_rejected():
    r = client.post("/api/v1/ingest", json=_event(source_system="   "))
    assert r.status_code == 422


def test_empty_payload_rejected():
    r = client.post("/api/v1/ingest", json=_event(payload={}))
    assert r.status_code == 422


def test_stale_timestamp_rejected():
    stale = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
    r = client.post("/api/v1/ingest", json=_event(timestamp=stale))
    assert r.status_code == 422


def test_missing_event_type_rejected():
    data = _event()
    del data["event_type"]
    r = client.post("/api/v1/ingest", json=data)
    assert r.status_code == 422


# ── business validation ────────────────────────────────────────────────────

def test_validate_no_warnings_on_clean_event():
    warnings = validate(_incoming())
    assert warnings == []


def test_validate_warns_missing_user_id_for_user_action():
    event    = _incoming(payload={"risk_hint": 0.5})
    warnings = validate(event)
    assert any("user_id" in w for w in warnings)


def test_validate_warns_missing_amount_for_transaction():
    event    = _incoming(
        event_type="transaction",
        payload={"user_id": "u1", "risk_hint": 0.5}
    )
    warnings = validate(event)
    assert any("amount" in w for w in warnings)


def test_validate_warns_non_numeric_risk_hint():
    event    = _incoming(payload={"user_id": "u1", "risk_hint": "high"})
    warnings = validate(event)
    assert any("risk_hint" in w for w in warnings)


def test_validate_warns_out_of_range_risk_hint():
    event    = _incoming(payload={"user_id": "u1", "risk_hint": 1.5})
    warnings = validate(event)
    assert any("risk_hint" in w for w in warnings)


def test_validate_in_range_risk_hint_no_warning():
    event    = _incoming(payload={"user_id": "u1", "risk_hint": 0.8})
    warnings = validate(event)
    assert not any("risk_hint" in w for w in warnings)


# ── enrichment ─────────────────────────────────────────────────────────────

def test_enrich_extracts_risk_hint():
    enriched = enrich(_incoming(payload={"user_id": "u1", "risk_hint": 0.75}))
    assert enriched.risk_hint == pytest.approx(0.75)


def test_enrich_clamps_risk_hint_above_one():
    enriched = enrich(_incoming(payload={"user_id": "u1", "risk_hint": 1.5}))
    assert enriched.risk_hint == pytest.approx(1.0)


def test_enrich_clamps_risk_hint_below_zero():
    enriched = enrich(_incoming(payload={"user_id": "u1", "risk_hint": -0.5}))
    assert enriched.risk_hint == pytest.approx(0.0)


def test_enrich_none_risk_hint_when_missing():
    enriched = enrich(_incoming(payload={"user_id": "u1"}))
    assert enriched.risk_hint is None


def test_enrich_none_risk_hint_when_non_numeric():
    enriched = enrich(_incoming(payload={"user_id": "u1", "risk_hint": "bad"}))
    assert enriched.risk_hint is None


def test_enrich_extracts_user_id():
    enriched = enrich(_incoming(payload={"user_id": "u-999", "risk_hint": 0.5}))
    assert enriched.user_id == "u-999"


def test_enrich_user_id_none_when_missing():
    enriched = enrich(_incoming(payload={"risk_hint": 0.5}))
    assert enriched.user_id is None


def test_enrich_is_high_value_fraud_category():
    enriched = enrich(_incoming(
        payload={"user_id": "u1", "risk_hint": 0.5, "category": "fraud"}
    ))
    assert enriched.is_high_value is True


def test_enrich_is_high_value_policy_violation():
    enriched = enrich(_incoming(
        payload={"user_id": "u1", "risk_hint": 0.5, "category": "policy_violation"}
    ))
    assert enriched.is_high_value is True


def test_enrich_is_high_value_high_risk_hint():
    enriched = enrich(_incoming(
        payload={"user_id": "u1", "risk_hint": 0.95, "category": "normal"}
    ))
    assert enriched.is_high_value is True


def test_enrich_is_high_value_large_amount():
    enriched = enrich(_incoming(
        event_type="transaction",
        payload={"user_id": "u1", "risk_hint": 0.3, "amount": 50_000}
    ))
    assert enriched.is_high_value is True


def test_enrich_not_high_value_normal_event():
    enriched = enrich(_incoming(
        payload={"user_id": "u1", "risk_hint": 0.3, "category": "normal"}
    ))
    assert enriched.is_high_value is False


def test_enrich_normalised_type_user_action():
    enriched = enrich(_incoming(event_type="user_action"))
    assert enriched.normalised_type == "behavioural"


def test_enrich_normalised_type_transaction():
    enriched = enrich(_incoming(
        event_type="transaction",
        payload={"user_id": "u1", "amount": 100, "risk_hint": 0.5}
    ))
    assert enriched.normalised_type == "financial"


def test_enrich_normalised_type_moderation():
    enriched = enrich(_incoming(event_type="moderation_decision"))
    assert enriched.normalised_type == "moderation"


def test_enrich_latency_ms_positive():
    enriched = enrich(_incoming())
    assert enriched.latency_ms >= 0.0


def test_enrich_schema_version():
    enriched = enrich(_incoming())
    assert enriched.schema_version == "1.0"


def test_enrich_ingestion_ts_set():
    enriched = enrich(_incoming())
    assert enriched.ingestion_ts is not None


# ── topic routing ──────────────────────────────────────────────────────────

def test_review_outcome_routes_to_review_queue():
    mock = _mock_producer()
    with patch("api.routes.ingest.get_producer", return_value=mock):
        r = client.post("/api/v1/ingest", json=_event(
            event_type="review_outcome",
            payload={"user_id": "u1", "risk_hint": 0.5, "decision": "positive"}
        ))
    assert r.status_code == 202
    call_args = mock.send.call_args[0]
    assert call_args[0] == "review-queue"


def test_transaction_routes_to_raw_events():
    mock = _mock_producer()
    with patch("api.routes.ingest.get_producer", return_value=mock):
        r = client.post("/api/v1/ingest", json=_event(
            event_type="transaction",
            payload={"user_id": "u1", "risk_hint": 0.5, "amount": 100}
        ))
    assert r.status_code == 202
    call_args = mock.send.call_args[0]
    assert call_args[0] == "raw-events"


# ── response body ──────────────────────────────────────────────────────────

def test_response_contains_event_id():
    with patch("api.routes.ingest.get_producer", return_value=_mock_producer()):
        r = client.post("/api/v1/ingest", json=_event())
    assert "event_id" in r.json()


def test_response_contains_enriched_fields():
    with patch("api.routes.ingest.get_producer", return_value=_mock_producer()):
        r = client.post("/api/v1/ingest", json=_event())
    body = r.json()
    assert "enriched"        in body
    assert "risk_hint"       in body["enriched"]
    assert "is_high_value"   in body["enriched"]
    assert "normalised_type" in body["enriched"]
    assert "latency_ms"      in body["enriched"]


def test_response_contains_warnings_field():
    with patch("api.routes.ingest.get_producer", return_value=_mock_producer()):
        r = client.post("/api/v1/ingest", json=_event())
    assert "warnings" in r.json()


def test_kafka_error_returns_503():
    from kafka.errors import KafkaError
    mock = _mock_producer()
    mock.send.side_effect = KafkaError("broker down")
    with patch("api.routes.ingest.get_producer", return_value=mock):
        r = client.post("/api/v1/ingest", json=_event())
    assert r.status_code == 503


# ── health endpoints ───────────────────────────────────────────────────────

def test_healthz_returns_ok():
    r = client.get("/api/v1/healthz")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_readyz_returns_ready():
    with patch("api.routes.ingest.get_producer", return_value=_mock_producer()):
        r = client.get("/api/v1/readyz")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"