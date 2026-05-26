from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, Literal
from datetime import datetime, timezone
import uuid


class IncomingEvent(BaseModel):
    event_id:      str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type:    Literal[
        "user_action", "moderation_decision",
        "transaction", "review_outcome", "operational_alert"
    ]
    source_system: str
    payload:       dict
    timestamp:     datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    metadata:      Optional[dict] = {}

    @field_validator("source_system")
    @classmethod
    def source_system_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("source_system must not be blank")
        return v.strip()

    @field_validator("payload")
    @classmethod
    def payload_not_empty(cls, v: dict) -> dict:
        if not v:
            raise ValueError("payload must not be empty")
        return v

    @field_validator("event_id")
    @classmethod
    def event_id_valid(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("event_id must not be blank")
        return v.strip()

    @model_validator(mode="after")
    def timestamp_not_too_stale(self) -> "IncomingEvent":
        # skip check on subclasses — EnrichedEvent re-uses the
        # already-validated timestamp from IncomingEvent
        if type(self) is not IncomingEvent:
            return self
        now = datetime.now(timezone.utc)
        ts  = self.timestamp
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        age = (now - ts).total_seconds()
        if age > 86400:
            raise ValueError(
                f"timestamp is {age:.0f}s old — older than 24h threshold"
            )
        return self


class EnrichedEvent(IncomingEvent):
    ingestion_ts:    datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    schema_version:  str = "1.0"
    risk_hint:       Optional[float] = None
    user_id:         Optional[str]   = None
    is_high_value:   Optional[bool]  = None
    normalised_type: Optional[str]   = None
    latency_ms:      Optional[float] = None