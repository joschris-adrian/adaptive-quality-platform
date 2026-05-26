import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from services.analytics.repository import (
    DecisionRepository,
    ReviewRepository,
    QualitySnapshotRepository,
    RCARepository,
    ExperimentRepository,
)


# ── helpers ────────────────────────────────────────────────────────────────

def _decision(event_id="evt-001", tier="standard", category="fraud",
              predicted="positive", ground_truth=None, risk_score=0.75,
              reviewer_id=None, escalated=False, reversed_=False,
              reviewed_at=None):
    return {
        "event_id":    event_id,
        "tier":        tier,
        "category":    category,
        "predicted":   predicted,
        "ground_truth": ground_truth,
        "risk_score":  risk_score,
        "reviewer_id": reviewer_id,
        "escalated":   escalated,
        "reversed":    reversed_,
        "reviewed_at": reviewed_at,
    }


def _review(event_id="evt-001", reviewer_id="r1",
            reviewer_group="standard", decision="positive",
            agreement_score=0.9):
    return {
        "event_id":       event_id,
        "reviewer_id":    reviewer_id,
        "reviewer_group": reviewer_group,
        "decision":       decision,
        "agreement_score": agreement_score,
    }


def _snapshot(total=100, labelled=80, precision=0.88, recall=0.82,
              f1=0.85, fpr=0.05, fnr=0.10, esc=0.20, rev=0.03):
    return {
        "total_decisions":     total,
        "labelled_count":      labelled,
        "precision":           precision,
        "recall":              recall,
        "f1":                  f1,
        "false_positive_rate": fpr,
        "false_negative_rate": fnr,
        "escalation_rate":     esc,
        "reversal_rate":       rev,
    }


def _failure(event_id="f001", tier="standard", category="fraud",
             failure_type="false_positive", risk_score=0.7):
    return {
        "event_id":    event_id,
        "tier":        tier,
        "category":    category,
        "failure_type": failure_type,
        "risk_score":  risk_score,
        "signals":     json.dumps({"ml": {"risk_probability": 0.7}}),
        "reviewer_id": None,
        "metadata":    json.dumps({}),
    }


def _experiment(experiment_id="exp-001"):
    return {
        "experiment_id": experiment_id,
        "name":          "test-exp",
        "description":   "test",
        "variants":      json.dumps(["control", "treatment"]),
        "metrics":       json.dumps(["precision", "cost"]),
        "traffic_split": json.dumps({"control": 0.5, "treatment": 0.5}),
        "status":        "draft",
        "metadata":      json.dumps({}),
    }


NOW = datetime.now(timezone.utc)
FROM_TS = NOW - timedelta(days=7)


# ── DecisionRepository ─────────────────────────────────────────────────────

class TestDecisionRepository:

    def test_insert_decision_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().insert_decision(_decision())
        mock_write.assert_called_once()

    def test_insert_decision_sql_contains_insert(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().insert_decision(_decision())
        sql = mock_write.call_args[0][0]
        assert "INSERT INTO decisions" in sql

    def test_insert_decision_passes_event_id(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().insert_decision(_decision(event_id="evt-xyz"))
        params = mock_write.call_args[0][1]
        assert params["event_id"] == "evt-xyz"

    def test_insert_decision_on_conflict_do_nothing(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().insert_decision(_decision())
        sql = mock_write.call_args[0][0]
        assert "ON CONFLICT" in sql
        assert "DO NOTHING"  in sql

    def test_update_ground_truth_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().update_ground_truth("evt-001", "positive")
        mock_write.assert_called_once()

    def test_update_ground_truth_sql_contains_update(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().update_ground_truth("evt-001", "positive")
        sql = mock_write.call_args[0][0]
        assert "UPDATE decisions" in sql
        assert "ground_truth"     in sql

    def test_update_ground_truth_passes_correct_params(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().update_ground_truth("evt-001", "negative")
        params = mock_write.call_args[0][1]
        assert params["event_id"]      == "evt-001"
        assert params["ground_truth"]  == "negative"

    def test_mark_reversed_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().mark_reversed("evt-001")
        mock_write.assert_called_once()

    def test_mark_reversed_sql_sets_reversed_true(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            DecisionRepository().mark_reversed("evt-001")
        sql = mock_write.call_args[0][0]
        assert "reversed = TRUE" in sql

    def test_queue_backlog_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            DecisionRepository().queue_backlog()
        mock_query.assert_called_once()

    def test_throughput_last_hour_returns_int(self):
        with patch("services.analytics.repository.execute_one",
                   return_value={"decisions_last_hour": 42}):
            result = DecisionRepository().throughput_last_hour()
        assert result == 42

    def test_throughput_last_hour_none_returns_zero(self):
        with patch("services.analytics.repository.execute_one", return_value=None):
            result = DecisionRepository().throughput_last_hour()
        assert result == 0

    def test_escalation_rate_passes_timestamps(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            DecisionRepository().escalation_rate(FROM_TS, NOW)
        params = mock_query.call_args[0][1]
        assert params["from_ts"] == FROM_TS
        assert params["to_ts"]   == NOW

    def test_precision_recall_by_tier_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            DecisionRepository().precision_recall_by_tier()
        mock_query.assert_called_once()

    def test_precision_recall_by_category_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            DecisionRepository().precision_recall_by_category()
        mock_query.assert_called_once()

    def test_false_positive_trend_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            DecisionRepository().false_positive_trend()
        mock_query.assert_called_once()

    def test_reversal_rate_by_category_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            DecisionRepository().reversal_rate_by_category()
        mock_query.assert_called_once()

    def test_risk_score_distribution_passes_timestamps(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            DecisionRepository().risk_score_distribution(FROM_TS, NOW)
        params = mock_query.call_args[0][1]
        assert "from_ts" in params
        assert "to_ts"   in params

    def test_priority_distribution_shift_passes_timestamps(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            DecisionRepository().priority_distribution_shift(FROM_TS, NOW)
        params = mock_query.call_args[0][1]
        assert "from_ts" in params
        assert "to_ts"   in params


# ── ReviewRepository ───────────────────────────────────────────────────────

class TestReviewRepository:

    def test_insert_review_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ReviewRepository().insert_review(_review())
        mock_write.assert_called_once()

    def test_insert_review_sql_contains_insert(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ReviewRepository().insert_review(_review())
        sql = mock_write.call_args[0][0]
        assert "INSERT INTO reviews" in sql

    def test_insert_review_passes_all_fields(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ReviewRepository().insert_review(_review(
                event_id="evt-r1", reviewer_id="r99",
                reviewer_group="expert", decision="negative",
                agreement_score=0.75,
            ))
        params = mock_write.call_args[0][1]
        assert params["event_id"]        == "evt-r1"
        assert params["reviewer_id"]     == "r99"
        assert params["reviewer_group"]  == "expert"
        assert params["decision"]        == "negative"
        assert params["agreement_score"] == 0.75

    def test_agreement_by_group_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            ReviewRepository().agreement_by_group()
        mock_query.assert_called_once()


# ── QualitySnapshotRepository ─────────────────────────────────────────────

class TestQualitySnapshotRepository:

    def test_insert_snapshot_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            QualitySnapshotRepository().insert_snapshot(_snapshot())
        mock_write.assert_called_once()

    def test_insert_snapshot_sql_contains_insert(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            QualitySnapshotRepository().insert_snapshot(_snapshot())
        sql = mock_write.call_args[0][0]
        assert "INSERT INTO quality_snapshots" in sql

    def test_insert_snapshot_passes_all_fields(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            QualitySnapshotRepository().insert_snapshot(
                _snapshot(precision=0.91, recall=0.87)
            )
        params = mock_write.call_args[0][1]
        assert params["precision"] == 0.91
        assert params["recall"]    == 0.87

    def test_trend_passes_timestamps(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            QualitySnapshotRepository().trend(FROM_TS, NOW)
        params = mock_query.call_args[0][1]
        assert params["from_ts"] == FROM_TS
        assert params["to_ts"]   == NOW

    def test_latest_calls_execute_one(self):
        with patch("services.analytics.repository.execute_one",
                   return_value=None) as mock_one:
            QualitySnapshotRepository().latest()
        mock_one.assert_called_once()

    def test_latest_returns_none_when_no_data(self):
        with patch("services.analytics.repository.execute_one", return_value=None):
            result = QualitySnapshotRepository().latest()
        assert result is None


# ── RCARepository ──────────────────────────────────────────────────────────

class TestRCARepository:

    def test_insert_failure_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            RCARepository().insert_failure(_failure())
        mock_write.assert_called_once()

    def test_insert_failure_sql_contains_insert(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            RCARepository().insert_failure(_failure())
        sql = mock_write.call_args[0][0]
        assert "INSERT INTO rca_failures" in sql

    def test_insert_failure_passes_failure_type(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            RCARepository().insert_failure(_failure(failure_type="false_negative"))
        params = mock_write.call_args[0][1]
        assert params["failure_type"] == "false_negative"

    def test_failure_modes_passes_from_ts(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            RCARepository().failure_modes(FROM_TS)
        params = mock_query.call_args[0][1]
        assert params["from_ts"] == FROM_TS

    def test_signal_means_passes_from_ts(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            RCARepository().signal_means(FROM_TS)
        params = mock_query.call_args[0][1]
        assert params["from_ts"] == FROM_TS

    def test_top_disagreeing_reviewers_default_limit(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            RCARepository().top_disagreeing_reviewers()
        params = mock_query.call_args[0][1]
        assert params["limit"] == 10

    def test_top_disagreeing_reviewers_custom_limit(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            RCARepository().top_disagreeing_reviewers(limit=5)
        params = mock_query.call_args[0][1]
        assert params["limit"] == 5

    def test_category_drift_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            RCARepository().category_drift()
        mock_query.assert_called_once()

    def test_emerging_categories_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            RCARepository().emerging_categories()
        mock_query.assert_called_once()


# ── ExperimentRepository ───────────────────────────────────────────────────

class TestExperimentRepository:

    def test_insert_experiment_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ExperimentRepository().insert_experiment(_experiment())
        mock_write.assert_called_once()

    def test_insert_experiment_sql_contains_insert(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ExperimentRepository().insert_experiment(_experiment())
        sql = mock_write.call_args[0][0]
        assert "INSERT INTO experiments" in sql

    def test_insert_experiment_on_conflict_do_nothing(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ExperimentRepository().insert_experiment(_experiment())
        sql = mock_write.call_args[0][0]
        assert "ON CONFLICT"  in sql
        assert "DO NOTHING"   in sql

    def test_update_status_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ExperimentRepository().update_status("exp-001", "running")
        mock_write.assert_called_once()

    def test_update_status_passes_status(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ExperimentRepository().update_status("exp-001", "completed",
                                                  completed_at=NOW)
        params = mock_write.call_args[0][1]
        assert params["status"]       == "completed"
        assert params["completed_at"] == NOW

    def test_insert_observation_calls_execute_write(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ExperimentRepository().insert_observation({
                "experiment_id": "exp-001",
                "variant":       "control",
                "event_id":      "evt-001",
                "metrics":       json.dumps({"precision": 0.88}),
            })
        mock_write.assert_called_once()

    def test_insert_observation_sql_contains_insert(self):
        with patch("services.analytics.repository.execute_write") as mock_write:
            ExperimentRepository().insert_observation({
                "experiment_id": "exp-001",
                "variant":       "control",
                "event_id":      "evt-001",
                "metrics":       json.dumps({}),
            })
        sql = mock_write.call_args[0][0]
        assert "INSERT INTO experiment_observations" in sql

    def test_results_passes_experiment_id_and_metric(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            ExperimentRepository().results("exp-001", "precision")
        params = mock_query.call_args[0][1]
        assert params["experiment_id"] == "exp-001"
        assert params["metric"]        == "precision"

    def test_active_experiments_calls_execute_query(self):
        with patch("services.analytics.repository.execute_query",
                   return_value=[]) as mock_query:
            ExperimentRepository().active_experiments()
        mock_query.assert_called_once()