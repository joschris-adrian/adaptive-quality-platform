import pytest
from unittest.mock import MagicMock, patch
from dashboards.snapshot_writer import write_snapshot
from services.analytics.metrics import QualityAnalyticsEngine


@pytest.fixture
def engine():
    e = QualityAnalyticsEngine()
    for i in range(10):
        e.record_decision(f"e{i}", "standard", "fraud", "positive", 0.8)
        e.record_ground_truth(f"e{i}", "positive")
    for i in range(10, 15):
        e.record_decision(f"e{i}", "standard", "fraud", "positive", 0.6)
        e.record_ground_truth(f"e{i}", "negative")
    return e


@pytest.fixture
def mock_conn():
    cursor = MagicMock()

    # make cursor work as a context manager: `with conn.cursor() as cur`
    cursor_ctx = MagicMock()
    cursor_ctx.__enter__ = MagicMock(return_value=cursor)
    cursor_ctx.__exit__  = MagicMock(return_value=False)

    conn = MagicMock()
    conn.cursor.return_value = cursor_ctx

    return conn, cursor


# ── write_snapshot ─────────────────────────────────────────────────────────

def test_write_snapshot_calls_execute(engine, mock_conn):
    conn, cursor = mock_conn
    with patch("dashboards.snapshot_writer.psycopg2.connect", return_value=conn):
        write_snapshot(engine)
    cursor.execute.assert_called_once()


def test_write_snapshot_commits(engine, mock_conn):
    conn, cursor = mock_conn
    with patch("dashboards.snapshot_writer.psycopg2.connect", return_value=conn):
        write_snapshot(engine)
    conn.commit.assert_called_once()


def test_write_snapshot_closes_connection(engine, mock_conn):
    conn, cursor = mock_conn
    with patch("dashboards.snapshot_writer.psycopg2.connect", return_value=conn):
        write_snapshot(engine)
    conn.close.assert_called_once()


def test_write_snapshot_closes_on_execute_error(engine, mock_conn):
    conn, cursor = mock_conn
    cursor.execute.side_effect = Exception("db error")
    with patch("dashboards.snapshot_writer.psycopg2.connect", return_value=conn):
        with pytest.raises(Exception, match="db error"):
            write_snapshot(engine)
    conn.close.assert_called_once()


def test_write_snapshot_inserts_correct_fields(engine, mock_conn):
    conn, cursor = mock_conn
    with patch("dashboards.snapshot_writer.psycopg2.connect", return_value=conn):
        write_snapshot(engine)

    args       = cursor.execute.call_args[0]
    sql, values = args[0], args[1]

    assert "INSERT INTO quality_snapshots" in sql
    assert "precision"           in sql
    assert "recall"              in sql
    assert "f1"                  in sql
    assert "false_positive_rate" in sql
    assert "false_negative_rate" in sql
    assert "escalation_rate"     in sql
    assert "reversal_rate"       in sql
    assert len(values)           == 9


def test_write_snapshot_values_are_floats(engine, mock_conn):
    conn, cursor = mock_conn
    with patch("dashboards.snapshot_writer.psycopg2.connect", return_value=conn):
        write_snapshot(engine)

    values = cursor.execute.call_args[0][1]
    assert isinstance(values[0], int)    # total_decisions
    assert isinstance(values[1], int)    # labelled_count
    for v in values[2:]:
        assert isinstance(v, float)


def test_write_snapshot_precision_in_range(engine, mock_conn):
    conn, cursor = mock_conn
    with patch("dashboards.snapshot_writer.psycopg2.connect", return_value=conn):
        write_snapshot(engine)

    values    = cursor.execute.call_args[0][1]
    precision = values[2]
    assert 0.0 <= precision <= 1.0


def test_write_snapshot_total_decisions_correct(engine, mock_conn):
    conn, cursor = mock_conn
    with patch("dashboards.snapshot_writer.psycopg2.connect", return_value=conn):
        write_snapshot(engine)

    values          = cursor.execute.call_args[0][1]
    total_decisions = values[0]
    assert total_decisions == 15

