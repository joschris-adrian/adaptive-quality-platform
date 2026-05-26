import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx
import random
import uuid
from datetime import datetime, timezone

EVENT_TYPES = [
    "user_action", "moderation_decision",
    "transaction", "review_outcome", "operational_alert"
]
VALID_SOURCE_SYSTEMS = ["web", "mobile", "api"]
VALID_CATEGORIES     = ["spam", "fraud", "policy_violation", "normal"]


def generate_event():
    event_type = random.choice(EVENT_TYPES)
    payload = {
        "user_id":   str(uuid.uuid4()),
        "risk_hint": round(random.random(), 3),
        "category":  random.choice(VALID_CATEGORIES),
    }
    if event_type == "transaction":
        payload["amount"] = round(random.uniform(10.0, 50_000.0), 2)

    return {
        "event_type":    event_type,
        "source_system": random.choice(VALID_SOURCE_SYSTEMS),
        "payload":       payload,
        "timestamp":     datetime.now(timezone.utc).isoformat(),
    }


def seed(n=500, url="http://localhost:8000/api/v1/ingest"):
    with httpx.Client(timeout=10.0) as client:
        for i in range(n):
            try:
                r = client.post(url, json=generate_event())
                print(f"[{i+1}/{n}] {r.status_code} "
                      f"{r.json().get('event_id', r.text)[:40]}")
            except httpx.ConnectError:
                print(f"[{i+1}/{n}] Connection refused — is the API running?")
                break
            except httpx.ReadTimeout:
                print(f"[{i+1}/{n}] Timeout — is Kafka running?")
                break


if __name__ == "__main__":
    seed()