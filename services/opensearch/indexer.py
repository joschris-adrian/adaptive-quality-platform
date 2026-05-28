from datetime import datetime, timezone
from services.opensearch.client import get_client


INDICES = {
    "decisions":     "decisions",
    "rca_failures":  "rca_failures",
    "dlq_events":    "dlq_events",
    "review_outcomes": "review_outcomes",
}


def _ensure_index(index: str):
    client = get_client()
    if not client.indices.exists(index=index):
        client.indices.create(index=index)


def index_decision(decision: dict):
    _ensure_index(INDICES["decisions"])
    doc = {**decision, "indexed_at": datetime.now(timezone.utc).isoformat()}
    get_client().index(index=INDICES["decisions"], body=doc)


def index_rca_failure(failure: dict):
    _ensure_index(INDICES["rca_failures"])
    doc = {**failure, "indexed_at": datetime.now(timezone.utc).isoformat()}
    get_client().index(index=INDICES["rca_failures"], body=doc)


def index_dlq_event(event: dict):
    _ensure_index(INDICES["dlq_events"])
    doc = {**event, "indexed_at": datetime.now(timezone.utc).isoformat()}
    get_client().index(index=INDICES["dlq_events"], body=doc)


def index_review_outcome(outcome: dict):
    _ensure_index(INDICES["review_outcomes"])
    doc = {**outcome, "indexed_at": datetime.now(timezone.utc).isoformat()}
    get_client().index(index=INDICES["review_outcomes"], body=doc)


def search(index: str, query: dict) -> list:
    _ensure_index(index)
    response = get_client().search(index=index, body=query)
    return [hit["_source"] for hit in response["hits"]["hits"]]