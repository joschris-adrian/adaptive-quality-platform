import logging
from datetime import datetime, timezone, timedelta
from sql.queries import (
    QUEUE_BACKLOG_BY_TIER,
    THROUGHPUT_LAST_HOUR,
    ESCALATION_RATE_OVER_TIME,
    PRECISION_RECALL_BY_TIER,
    PRECISION_RECALL_BY_CATEGORY,
    FALSE_POSITIVE_TREND,
    REVERSAL_RATE_BY_CATEGORY,
    QUALITY_SNAPSHOT_TREND,
    REVIEWER_AGREEMENT_BY_GROUP,
    CATEGORY_DRIFT,
    EMERGING_FAILURE_CATEGORIES,
    RISK_SCORE_DISTRIBUTION,
    PRIORITY_DISTRIBUTION_SHIFT,
    RCA_FAILURE_MODES,
    RCA_SIGNAL_MEANS,
    RCA_TOP_DISAGREEING_REVIEWERS,
    EXPERIMENT_RESULTS_SUMMARY,
    ACTIVE_EXPERIMENTS,
)
from services.analytics.db import execute_query, execute_one, execute_write

logger = logging.getLogger(__name__)


class DecisionRepository:

    def insert_decision(self, decision: dict):
        execute_write("""
            INSERT INTO decisions (
                event_id, tier, category, predicted,
                ground_truth, risk_score, reviewer_id,
                escalated, reversed, reviewed_at
            ) VALUES (
                %(event_id)s, %(tier)s, %(category)s, %(predicted)s,
                %(ground_truth)s, %(risk_score)s, %(reviewer_id)s,
                %(escalated)s, %(reversed)s, %(reviewed_at)s
            )
            ON CONFLICT (event_id) DO NOTHING;
        """, decision)

    def update_ground_truth(self, event_id: str, ground_truth: str):
        execute_write("""
            UPDATE decisions
            SET ground_truth = %(ground_truth)s,
                reviewed_at  = NOW()
            WHERE event_id = %(event_id)s;
        """, {"event_id": event_id, "ground_truth": ground_truth})

    def mark_reversed(self, event_id: str):
        execute_write("""
            UPDATE decisions
            SET reversed = TRUE
            WHERE event_id = %(event_id)s;
        """, {"event_id": event_id})

    def queue_backlog(self) -> list[dict]:
        return execute_query(QUEUE_BACKLOG_BY_TIER)

    def throughput_last_hour(self) -> int:
        row = execute_one(THROUGHPUT_LAST_HOUR)
        return row["decisions_last_hour"] if row else 0

    def escalation_rate(self, from_ts: datetime, to_ts: datetime) -> list[dict]:
        return execute_query(ESCALATION_RATE_OVER_TIME, {
            "from_ts": from_ts, "to_ts": to_ts
        })

    def precision_recall_by_tier(self) -> list[dict]:
        return execute_query(PRECISION_RECALL_BY_TIER)

    def precision_recall_by_category(self) -> list[dict]:
        return execute_query(PRECISION_RECALL_BY_CATEGORY)

    def false_positive_trend(self) -> list[dict]:
        return execute_query(FALSE_POSITIVE_TREND)

    def reversal_rate_by_category(self) -> list[dict]:
        return execute_query(REVERSAL_RATE_BY_CATEGORY)

    def risk_score_distribution(self, from_ts: datetime, to_ts: datetime) -> list[dict]:
        return execute_query(RISK_SCORE_DISTRIBUTION, {
            "from_ts": from_ts, "to_ts": to_ts
        })

    def priority_distribution_shift(self, from_ts: datetime, to_ts: datetime) -> list[dict]:
        return execute_query(PRIORITY_DISTRIBUTION_SHIFT, {
            "from_ts": from_ts, "to_ts": to_ts
        })


class ReviewRepository:

    def insert_review(self, review: dict):
        execute_write("""
            INSERT INTO reviews (
                event_id, reviewer_id, reviewer_group,
                decision, agreement_score
            ) VALUES (
                %(event_id)s, %(reviewer_id)s, %(reviewer_group)s,
                %(decision)s, %(agreement_score)s
            );
        """, review)

    def agreement_by_group(self) -> list[dict]:
        return execute_query(REVIEWER_AGREEMENT_BY_GROUP)


class QualitySnapshotRepository:

    def insert_snapshot(self, snap: dict):
        execute_write("""
            INSERT INTO quality_snapshots (
                total_decisions, labelled_count,
                precision, recall, f1,
                false_positive_rate, false_negative_rate,
                escalation_rate, reversal_rate
            ) VALUES (
                %(total_decisions)s, %(labelled_count)s,
                %(precision)s, %(recall)s, %(f1)s,
                %(false_positive_rate)s, %(false_negative_rate)s,
                %(escalation_rate)s, %(reversal_rate)s
            );
        """, snap)

    def trend(self, from_ts: datetime, to_ts: datetime) -> list[dict]:
        return execute_query(QUALITY_SNAPSHOT_TREND, {
            "from_ts": from_ts, "to_ts": to_ts
        })

    def latest(self) -> dict | None:
        return execute_one("""
            SELECT * FROM quality_snapshots
            ORDER BY snapshot_at DESC LIMIT 1;
        """)


class RCARepository:

    def insert_failure(self, failure: dict):
        execute_write("""
            INSERT INTO rca_failures (
                event_id, tier, category, failure_type,
                risk_score, signals, reviewer_id, metadata
            ) VALUES (
                %(event_id)s, %(tier)s, %(category)s, %(failure_type)s,
                %(risk_score)s, %(signals)s, %(reviewer_id)s, %(metadata)s
            );
        """, failure)

    def failure_modes(self, from_ts: datetime) -> list[dict]:
        return execute_query(RCA_FAILURE_MODES, {"from_ts": from_ts})

    def signal_means(self, from_ts: datetime) -> list[dict]:
        return execute_query(RCA_SIGNAL_MEANS, {"from_ts": from_ts})

    def top_disagreeing_reviewers(self, limit: int = 10) -> list[dict]:
        return execute_query(RCA_TOP_DISAGREEING_REVIEWERS, {"limit": limit})

    def category_drift(self) -> list[dict]:
        return execute_query(CATEGORY_DRIFT)

    def emerging_categories(self) -> list[dict]:
        return execute_query(EMERGING_FAILURE_CATEGORIES)


class ExperimentRepository:

    def insert_experiment(self, exp: dict):
        execute_write("""
            INSERT INTO experiments (
                experiment_id, name, description, variants,
                metrics, traffic_split, status, metadata
            ) VALUES (
                %(experiment_id)s, %(name)s, %(description)s,
                %(variants)s::jsonb, %(metrics)s::jsonb,
                %(traffic_split)s::jsonb, %(status)s,
                %(metadata)s::jsonb
            )
            ON CONFLICT (experiment_id) DO NOTHING;
        """, exp)

    def update_status(self, experiment_id: str, status: str,
                      started_at=None, completed_at=None):
        execute_write("""
            UPDATE experiments
            SET status       = %(status)s,
                started_at   = COALESCE(%(started_at)s,   started_at),
                completed_at = COALESCE(%(completed_at)s, completed_at)
            WHERE experiment_id = %(experiment_id)s;
        """, {
            "experiment_id": experiment_id,
            "status":        status,
            "started_at":    started_at,
            "completed_at":  completed_at,
        })

    def insert_observation(self, obs: dict):
        execute_write("""
            INSERT INTO experiment_observations (
                experiment_id, variant, event_id, metrics
            ) VALUES (
                %(experiment_id)s, %(variant)s,
                %(event_id)s, %(metrics)s::jsonb
            );
        """, obs)

    def results(self, experiment_id: str, metric: str) -> list[dict]:
        return execute_query(EXPERIMENT_RESULTS_SUMMARY, {
            "experiment_id": experiment_id,
            "metric":        metric,
        })

    def active_experiments(self) -> list[dict]:
        return execute_query(ACTIVE_EXPERIMENTS)