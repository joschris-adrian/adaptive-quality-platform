import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch, MagicMock


@patch("services.opensearch.indexer.get_client")
def test_index_decision_calls_index(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.indices.exists.return_value = True

    from services.opensearch.indexer import index_decision
    index_decision({"event_id": "e001", "risk_score": 0.72, "tier": "standard"})
    mock_client.index.assert_called_once()
    call_kwargs = mock_client.index.call_args[1]
    assert call_kwargs["index"] == "decisions"
    assert call_kwargs["body"]["event_id"] == "e001"


@patch("services.opensearch.indexer.get_client")
def test_index_rca_failure_calls_index(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.indices.exists.return_value = True

    from services.opensearch.indexer import index_rca_failure
    index_rca_failure({"event_id": "f001", "failure_type": "false_positive"})
    mock_client.index.assert_called_once()
    call_kwargs = mock_client.index.call_args[1]
    assert call_kwargs["index"] == "rca_failures"


@patch("services.opensearch.indexer.get_client")
def test_index_creates_index_if_missing(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.indices.exists.return_value = False

    from services.opensearch.indexer import index_decision
    index_decision({"event_id": "e002"})
    mock_client.indices.create.assert_called_once_with(index="decisions")


@patch("services.opensearch.indexer.get_client")
def test_index_adds_indexed_at_field(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.indices.exists.return_value = True

    from services.opensearch.indexer import index_decision
    index_decision({"event_id": "e003"})
    body = mock_client.index.call_args[1]["body"]
    assert "indexed_at" in body


@patch("services.opensearch.indexer.get_client")
def test_search_returns_sources(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.indices.exists.return_value = True
    mock_client.search.return_value = {
        "hits": {"hits": [{"_source": {"event_id": "e001"}}, {"_source": {"event_id": "e002"}}]}
    }

    from services.opensearch.indexer import search
    results = search("decisions", {"query": {"match_all": {}}})
    assert len(results) == 2
    assert results[0]["event_id"] == "e001"


@patch("services.opensearch.indexer.get_client")
def test_index_dlq_event(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.indices.exists.return_value = True

    from services.opensearch.indexer import index_dlq_event
    index_dlq_event({"event_id": "d001", "error": "broker down"})
    call_kwargs = mock_client.index.call_args[1]
    assert call_kwargs["index"] == "dlq_events"


@patch("services.opensearch.indexer.get_client")
def test_index_review_outcome(mock_get_client):
    mock_client = MagicMock()
    mock_get_client.return_value = mock_client
    mock_client.indices.exists.return_value = True

    from services.opensearch.indexer import index_review_outcome
    index_review_outcome({"event_id": "r001", "reviewer_id": "rev-1", "outcome": "approved"})
    call_kwargs = mock_client.index.call_args[1]
    assert call_kwargs["index"] == "review_outcomes"