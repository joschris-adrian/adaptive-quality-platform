import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import uuid
from unittest.mock import MagicMock, patch, call
from scripts.seed_database import (
    seed_decisions,
    seed_reviews,
    seed_quality_snapshots,
    seed_rca_failures,
    random_ts,
    TIERS,
    CATEGORIES,
    PREDICTED,
    REVIEWER_GROUPS,
)
from datetime import datetime, timezone


# ── helpers ────────────────────────────────────────────────────────────────

@pytest.fixture
def cursor():
    cur = MagicMock()
    cur.fetchone.return_value = (str(uuid.uuid4()),)
    return cur


# ── random_ts ─────────────────────────────────────────────────────────────

def test_random_ts_returns_datetime():
    ts = random_ts()
    assert isinstance(ts, datetime)


def test_random_ts_is_timezone_aware():
    ts = random_ts()
    assert ts.tzinfo is not None


def test_random_ts_is_in_the_past():
    ts = random_ts(days_ago_max=30)
    assert ts < datetime.now(timezone.utc)


def test_random_ts_within_range():
    from datetime import timedelta
    ts = random_ts(days_ago_max=1)
    assert ts >= datetime.now(timezone.utc) - timedelta(days=1, seconds=5)


def test_random_ts_zero_days_is_recent():
    from datetime import timedelta
    ts = random_ts(days_ago_max=0)
    assert ts >= datetime.now(timezone.utc) - timedelta(seconds=5)


# ── constants ─────────────────────────────────────────────────────────────

def test_tiers_not_empty():
    assert len(TIERS) > 0


def test_tiers_contains_expected():
    assert "automated" in TIERS
    assert "standard"  in TIERS
    assert "expert"    in TIERS


def test_categories_not_empty():
    assert len(CATEGORIES) > 0


def test_categories_contains_expected():
    assert "fraud"  in CATEGORIES
    assert "spam"   in CATEGORIES
    assert "clean"  in CATEGORIES


def test_predicted_contains_both():
    assert "positive" in PREDICTED
    assert "negative" in PREDICTED


def test_reviewer_groups_not_empty():
    assert len(REVIEWER_GROUPS) > 0


# ── seed_decisions ─────────────────────────────────────────────────────────

def test_seed_decisions_calls_execute_n_times(cursor):
    seed_decisions(cursor, n=10)
    assert cursor.execute.call_count == 10


def test_seed_decisions_inserts_into_decisions(cursor):
    seed_decisions(cursor, n=1)
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO decisions" in sql


def test_seed_decisions_on_conflict_do_nothing(cursor):
    seed_decisions(cursor, n=1)
    sql = cursor.execute.call_args[0][0]
    assert "ON CONFLICT" in sql
    assert "DO NOTHING"  in sql


def test_seed_decisions_correct_param_count(cursor):
    seed_decisions(cursor, n=1)
    params = cursor.execute.call_args[0][1]
    assert len(params) == 10


def test_seed_decisions_event_id_is_uuid(cursor):
    seed_decisions(cursor, n=1)
    params    = cursor.execute.call_args[0][1]
    event_id  = params[0]
    parsed    = uuid.UUID(event_id)
    assert str(parsed) == event_id


def test_seed_decisions_tier_is_valid(cursor):
    for _ in range(20):
        seed_decisions(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        assert params[1] in TIERS


def test_seed_decisions_category_is_valid(cursor):
    for _ in range(20):
        seed_decisions(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        assert params[2] in CATEGORIES


def test_seed_decisions_predicted_is_valid(cursor):
    for _ in range(20):
        seed_decisions(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        assert params[3] in PREDICTED


def test_seed_decisions_risk_score_in_range(cursor):
    for _ in range(20):
        seed_decisions(cursor, n=1)
        params     = cursor.execute.call_args[0][1]
        risk_score = params[5]
        assert 0.0 <= risk_score <= 1.0


def test_seed_decisions_escalated_is_bool(cursor):
    seed_decisions(cursor, n=1)
    params    = cursor.execute.call_args[0][1]
    escalated = params[6]
    assert isinstance(escalated, bool)


def test_seed_decisions_reversed_is_bool(cursor):
    seed_decisions(cursor, n=1)
    params   = cursor.execute.call_args[0][1]
    reversed_ = params[7]
    assert isinstance(reversed_, bool)


def test_seed_decisions_created_at_is_datetime(cursor):
    seed_decisions(cursor, n=1)
    params     = cursor.execute.call_args[0][1]
    created_at = params[8]
    assert isinstance(created_at, datetime)


def test_seed_decisions_zero_n_calls_nothing(cursor):
    seed_decisions(cursor, n=0)
    cursor.execute.assert_not_called()


# ── seed_reviews ───────────────────────────────────────────────────────────

def test_seed_reviews_calls_execute_n_times(cursor):
    seed_reviews(cursor, n=5)
    # one SELECT + one INSERT per review = 10 calls
    assert cursor.execute.call_count == 10


def test_seed_reviews_selects_random_event_id(cursor):
    seed_reviews(cursor, n=1)
    first_call_sql = cursor.execute.call_args_list[0][0][0]
    assert "SELECT event_id FROM decisions" in first_call_sql


def test_seed_reviews_inserts_into_reviews(cursor):
    seed_reviews(cursor, n=1)
    second_call_sql = cursor.execute.call_args_list[1][0][0]
    assert "INSERT INTO reviews" in second_call_sql


def test_seed_reviews_reviewer_group_is_valid(cursor):
    for _ in range(10):
        seed_reviews(cursor, n=1)
        params = cursor.execute.call_args_list[1][0][1]
        assert params[2] in REVIEWER_GROUPS


def test_seed_reviews_decision_is_valid(cursor):
    for _ in range(10):
        seed_reviews(cursor, n=1)
        params = cursor.execute.call_args_list[1][0][1]
        assert params[3] in PREDICTED


def test_seed_reviews_agreement_in_range(cursor):
    for _ in range(10):
        seed_reviews(cursor, n=1)
        params    = cursor.execute.call_args_list[1][0][1]
        agreement = params[4]
        assert 0.5 <= agreement <= 1.0


def test_seed_reviews_skips_when_no_decisions(cursor):
    cursor.fetchone.return_value = None
    seed_reviews(cursor, n=3)
    insert_calls = [
        c for c in cursor.execute.call_args_list
        if "INSERT" in c[0][0]
    ]
    assert len(insert_calls) == 0


def test_seed_reviews_zero_n_calls_nothing(cursor):
    seed_reviews(cursor, n=0)
    cursor.execute.assert_not_called()


# ── seed_quality_snapshots ────────────────────────────────────────────────

def test_seed_quality_snapshots_calls_execute_n_times(cursor):
    seed_quality_snapshots(cursor, n=5)
    assert cursor.execute.call_count == 5


def test_seed_quality_snapshots_inserts_correct_table(cursor):
    seed_quality_snapshots(cursor, n=1)
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO quality_snapshots" in sql


def test_seed_quality_snapshots_correct_param_count(cursor):
    seed_quality_snapshots(cursor, n=1)
    params = cursor.execute.call_args[0][1]
    assert len(params) == 10


def test_seed_quality_snapshots_precision_in_range(cursor):
    for _ in range(10):
        seed_quality_snapshots(cursor, n=1)
        params    = cursor.execute.call_args[0][1]
        precision = params[3]
        assert 0.0 <= precision <= 1.0


def test_seed_quality_snapshots_recall_in_range(cursor):
    for _ in range(10):
        seed_quality_snapshots(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        recall = params[4]
        assert 0.0 <= recall <= 1.0


def test_seed_quality_snapshots_f1_in_range(cursor):
    for _ in range(10):
        seed_quality_snapshots(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        f1     = params[5]
        assert 0.0 <= f1 <= 1.0


def test_seed_quality_snapshots_total_positive(cursor):
    seed_quality_snapshots(cursor, n=1)
    params = cursor.execute.call_args[0][1]
    total  = params[1]
    assert total > 0


def test_seed_quality_snapshots_labelled_lte_total(cursor):
    seed_quality_snapshots(cursor, n=1)
    params   = cursor.execute.call_args[0][1]
    total    = params[1]
    labelled = params[2]
    assert labelled <= total


def test_seed_quality_snapshots_snapshot_at_is_datetime(cursor):
    seed_quality_snapshots(cursor, n=1)
    params      = cursor.execute.call_args[0][1]
    snapshot_at = params[0]
    assert isinstance(snapshot_at, datetime)


def test_seed_quality_snapshots_snapshot_at_in_past(cursor):
    seed_quality_snapshots(cursor, n=1)
    params      = cursor.execute.call_args[0][1]
    snapshot_at = params[0]
    assert snapshot_at < datetime.now(timezone.utc)


def test_seed_quality_snapshots_snapshots_ordered_ascending(cursor):
    seed_quality_snapshots(cursor, n=5)
    timestamps = [
        cursor.execute.call_args_list[i][0][1][0]
        for i in range(5)
    ]
    assert timestamps == sorted(timestamps)


def test_seed_quality_snapshots_zero_n_calls_nothing(cursor):
    seed_quality_snapshots(cursor, n=0)
    cursor.execute.assert_not_called()


# ── seed_rca_failures ─────────────────────────────────────────────────────

VALID_FAILURE_TYPES = {
    "false_positive", "false_negative", "reversal", "disagreement"
}


def test_seed_rca_failures_calls_execute_n_times(cursor):
    seed_rca_failures(cursor, n=10)
    assert cursor.execute.call_count == 10


def test_seed_rca_failures_inserts_correct_table(cursor):
    seed_rca_failures(cursor, n=1)
    sql = cursor.execute.call_args[0][0]
    assert "INSERT INTO rca_failures" in sql


def test_seed_rca_failures_correct_param_count(cursor):
    seed_rca_failures(cursor, n=1)
    params = cursor.execute.call_args[0][1]
    assert len(params) == 7


def test_seed_rca_failures_event_id_is_uuid(cursor):
    seed_rca_failures(cursor, n=1)
    params   = cursor.execute.call_args[0][1]
    event_id = params[0]
    parsed   = uuid.UUID(event_id)
    assert str(parsed) == event_id


def test_seed_rca_failures_tier_is_valid(cursor):
    for _ in range(20):
        seed_rca_failures(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        assert params[1] in TIERS


def test_seed_rca_failures_category_is_valid(cursor):
    for _ in range(20):
        seed_rca_failures(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        assert params[2] in CATEGORIES


def test_seed_rca_failures_failure_type_is_valid(cursor):
    for _ in range(20):
        seed_rca_failures(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        assert params[3] in VALID_FAILURE_TYPES


def test_seed_rca_failures_risk_score_in_range(cursor):
    for _ in range(20):
        seed_rca_failures(cursor, n=1)
        params     = cursor.execute.call_args[0][1]
        risk_score = params[4]
        assert 0.3 <= risk_score <= 0.95


def test_seed_rca_failures_signals_is_valid_json(cursor):
    seed_rca_failures(cursor, n=1)
    params  = cursor.execute.call_args[0][1]
    signals = params[5]
    parsed  = json.loads(signals)
    assert "ml"        in parsed
    assert "rule"      in parsed
    assert "heuristic" in parsed


def test_seed_rca_failures_ml_probability_in_range(cursor):
    for _ in range(10):
        seed_rca_failures(cursor, n=1)
        params  = cursor.execute.call_args[0][1]
        signals = json.loads(params[5])
        prob    = signals["ml"]["risk_probability"]
        assert 0.3 <= prob <= 0.95


def test_seed_rca_failures_reviewer_id_is_string_or_none(cursor):
    for _ in range(20):
        seed_rca_failures(cursor, n=1)
        params      = cursor.execute.call_args[0][1]
        reviewer_id = params[6]
        assert reviewer_id is None or isinstance(reviewer_id, str)


def test_seed_rca_failures_zero_n_calls_nothing(cursor):
    seed_rca_failures(cursor, n=0)
    cursor.execute.assert_not_called()


def test_seed_rca_failures_produces_variety_of_failure_types(cursor):
    seen_types = set()
    for _ in range(100):
        seed_rca_failures(cursor, n=1)
        params = cursor.execute.call_args[0][1]
        seen_types.add(params[3])
    assert len(seen_types) >= 3


# ── main integration ───────────────────────────────────────────────────────

def test_main_calls_all_seed_functions():
    with patch("scripts.seed_database.psycopg2.connect") as mock_connect:
        mock_conn   = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = (str(uuid.uuid4()),)
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__  = MagicMock(return_value=False)
        mock_conn.cursor.return_value.__enter__ = MagicMock(
            return_value=mock_cursor
        )
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_connect.return_value = mock_conn

        from scripts.seed_database import main
        main()

    mock_connect.assert_called_once()
    mock_conn.commit.assert_called_once()
    mock_conn.close.assert_called_once()