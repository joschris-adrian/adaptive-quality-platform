from fastapi import APIRouter, HTTPException, Request
from api.schemas import IncomingEvent, EnrichedEvent
from kafka import KafkaProducer
from kafka.errors import KafkaError
import json
import logging
import os
import time

router = APIRouter()
logger = logging.getLogger(__name__)

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")

_producer = None


def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=[KAFKA_BOOTSTRAP],
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
            acks="all",
            retries=3,
            compression_type="gzip",
        )
    return _producer


TOPIC_MAP = {
    "user_action":          "raw-events",
    "moderation_decision":  "raw-events",
    "transaction":          "raw-events",
    "review_outcome":       "review-queue",
    "operational_alert":    "raw-events",
}

HIGH_VALUE_CATEGORIES = {"fraud", "policy_violation"}

TYPE_NORMALISATION = {
    "user_action":          "behavioural",
    "moderation_decision":  "moderation",
    "transaction":          "financial",
    "review_outcome":       "review",
    "operational_alert":    "operational",
}


def validate(event: IncomingEvent) -> list[str]:
    warnings = []
    risk_hint = event.payload.get("risk_hint")
    if risk_hint is not None:
        if not isinstance(risk_hint, (int, float)):
            warnings.append("risk_hint is not numeric — will be ignored")
        elif not (0.0 <= float(risk_hint) <= 1.0):
            warnings.append(f"risk_hint {risk_hint} is outside [0, 1] — will be clamped")
    if event.event_type == "user_action" and not event.payload.get("user_id"):
        warnings.append("user_action event is missing user_id in payload")
    if event.event_type == "transaction" and "amount" not in event.payload:
        warnings.append("transaction event is missing amount in payload")
    return warnings


def enrich(event: IncomingEvent) -> EnrichedEvent:
    t0      = time.perf_counter()
    payload = event.payload

    raw_hint = payload.get("risk_hint")
    if isinstance(raw_hint, (int, float)):
        risk_hint = float(max(0.0, min(1.0, raw_hint)))
    else:
        risk_hint = None

    user_id = str(payload.get("user_id", "")) or None

    category      = str(payload.get("category", ""))
    amount        = payload.get("amount", 0)
    is_high_value = (
        category in HIGH_VALUE_CATEGORIES
        or (isinstance(amount, (int, float)) and float(amount) > 10_000)
        or (risk_hint is not None and risk_hint >= 0.90)
    )

    normalised_type = TYPE_NORMALISATION.get(event.event_type, "unknown")
    latency_ms      = round((time.perf_counter() - t0) * 1000, 3)

    return EnrichedEvent(
        **event.model_dump(),
        risk_hint=       risk_hint,
        user_id=         user_id,
        is_high_value=   is_high_value,
        normalised_type= normalised_type,
        latency_ms=      latency_ms,
    )


@router.post("/ingest", status_code=202)
async def ingest_event(event: IncomingEvent, request: Request):
    warnings = validate(event)
    if warnings:
        for w in warnings:
            logger.warning(f"[{event.event_id}] validation warning: {w}")

    enriched = enrich(event)
    topic    = TOPIC_MAP.get(enriched.event_type, "raw-events")

    try:
        producer = get_producer()
        producer.send(
            topic,
            key=enriched.event_id.encode(),
            value=enriched.model_dump(),
        )
        producer.flush()
        logger.info(
            f"[{enriched.event_id}] → {topic} "
            f"risk_hint={enriched.risk_hint} "
            f"is_high_value={enriched.is_high_value} "
            f"latency={enriched.latency_ms}ms"
        )
    except KafkaError as e:
        logger.error(f"Kafka send failed for {enriched.event_id}: {e}")
        raise HTTPException(status_code=503, detail="Ingestion unavailable")

    return {
        "event_id":  enriched.event_id,
        "topic":     topic,
        "status":    "accepted",
        "warnings":  warnings,
        "enriched": {
            "risk_hint":       enriched.risk_hint,
            "user_id":         enriched.user_id,
            "is_high_value":   enriched.is_high_value,
            "normalised_type": enriched.normalised_type,
            "latency_ms":      enriched.latency_ms,
        },
    }


@router.get("/healthz")
async def healthz():
    return {"status": "ok"}


@router.get("/readyz")
async def readyz():
    try:
        get_producer().partitions_for("raw-events")
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Kafka not reachable: {e}")