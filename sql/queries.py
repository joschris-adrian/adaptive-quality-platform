# Every query is a module-level string constant.
# Use with psycopg2: cur.execute(QUERY, params)
# Use with SQLAlchemy: conn.execute(text(QUERY), params)

# ── Operational ───────────────────────────────────────────────────────────

EVENT_VOLUME_PER_MINUTE = """
SELECT
    DATE_TRUNC('minute', created_at)    AS bucket,
    tier,
    COUNT(*)                            AS event_count
FROM decisions
WHERE created_at >= %(from_ts)s
  AND created_at <= %(to_ts)s
GROUP BY bucket, tier
ORDER BY bucket;
"""

QUEUE_BACKLOG_BY_TIER = """
SELECT
    tier,
    COUNT(*) FILTER (WHERE reviewed_at IS NULL)      AS pending,
    COUNT(*) FILTER (WHERE reviewed_at IS NOT NULL)  AS completed,
    AVG(
        EXTRACT(EPOCH FROM (reviewed_at - created_at)) / 60
    ) FILTER (WHERE reviewed_at IS NOT NULL)         AS avg_review_minutes,
    MAX(
        EXTRACT(EPOCH FROM (NOW() - created_at)) / 60
    ) FILTER (WHERE reviewed_at IS NULL)             AS oldest_pending_minutes
FROM decisions
GROUP BY tier
ORDER BY pending DESC;
"""

DECISION_LATENCY_PERCENTILES = """
SELECT
    DATE_TRUNC('minute', created_at)                    AS bucket,
    PERCENTILE_CONT(0.50) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (reviewed_at - created_at)) / 60
    )                                                   AS p50_minutes,
    PERCENTILE_CONT(0.95) WITHIN GROUP (
        ORDER BY EXTRACT(EPOCH FROM (reviewed_at - created_at)) / 60
    )                                                   AS p95_minutes
FROM decisions
WHERE reviewed_at IS NOT NULL
  AND created_at >= %(from_ts)s
  AND created_at <= %(to_ts)s
GROUP BY bucket
ORDER BY bucket;
"""

THROUGHPUT_LAST_HOUR = """
SELECT COUNT(*) AS decisions_last_hour
FROM decisions
WHERE created_at >= NOW() - INTERVAL '1 hour';
"""

ACTION_DISTRIBUTION = """
SELECT
    tier,
    COUNT(*)                            AS count,
    ROUND(COUNT(*)::numeric /
        NULLIF(SUM(COUNT(*)) OVER (), 0), 4) AS fraction
FROM decisions
WHERE created_at >= %(from_ts)s
GROUP BY tier
ORDER BY count DESC;
"""

ESCALATION_RATE_OVER_TIME = """
SELECT
    DATE_TRUNC('hour', created_at)      AS bucket,
    COUNT(*)                            AS total,
    SUM(escalated::int)                 AS escalated,
    ROUND(AVG(escalated::int)::numeric, 4) AS escalation_rate
FROM decisions
WHERE created_at >= %(from_ts)s
  AND created_at <= %(to_ts)s
GROUP BY bucket
ORDER BY bucket;
"""

# ── Quality ───────────────────────────────────────────────────────────────

PRECISION_RECALL_BY_TIER = """
SELECT
    tier,
    COUNT(*) FILTER (
        WHERE predicted = 'positive' AND ground_truth = 'positive'
    )                                                   AS tp,
    COUNT(*) FILTER (
        WHERE predicted = 'positive' AND ground_truth = 'negative'
    )                                                   AS fp,
    COUNT(*) FILTER (
        WHERE predicted = 'negative' AND ground_truth = 'negative'
    )                                                   AS tn,
    COUNT(*) FILTER (
        WHERE predicted = 'negative' AND ground_truth = 'positive'
    )                                                   AS fn,
    ROUND(
        COUNT(*) FILTER (
            WHERE predicted = 'positive' AND ground_truth = 'positive'
        )::numeric /
        NULLIF(COUNT(*) FILTER (WHERE predicted = 'positive'), 0),
    4)                                                  AS precision,
    ROUND(
        COUNT(*) FILTER (
            WHERE predicted = 'positive' AND ground_truth = 'positive'
        )::numeric /
        NULLIF(
            COUNT(*) FILTER (
                WHERE predicted = 'positive' AND ground_truth = 'positive'
            ) +
            COUNT(*) FILTER (
                WHERE predicted = 'negative' AND ground_truth = 'positive'
            ), 0
        ),
    4)                                                  AS recall,
    COUNT(*)                                            AS total
FROM decisions
WHERE ground_truth IS NOT NULL
GROUP BY tier
ORDER BY tier;
"""

PRECISION_RECALL_BY_CATEGORY = """
SELECT
    category,
    COUNT(*) FILTER (
        WHERE predicted = 'positive' AND ground_truth = 'positive'
    )                                                   AS tp,
    COUNT(*) FILTER (
        WHERE predicted = 'positive' AND ground_truth = 'negative'
    )                                                   AS fp,
    ROUND(
        COUNT(*) FILTER (
            WHERE predicted = 'positive' AND ground_truth = 'positive'
        )::numeric /
        NULLIF(COUNT(*) FILTER (WHERE predicted = 'positive'), 0),
    4)                                                  AS precision,
    ROUND(
        COUNT(*) FILTER (
            WHERE predicted = 'positive' AND ground_truth = 'positive'
        )::numeric /
        NULLIF(
            COUNT(*) FILTER (
                WHERE predicted = 'positive' AND ground_truth = 'positive'
            ) +
            COUNT(*) FILTER (
                WHERE predicted = 'negative' AND ground_truth = 'positive'
            ), 0
        ),
    4)                                                  AS recall,
    COUNT(*)                                            AS total
FROM decisions
WHERE ground_truth IS NOT NULL
GROUP BY category
ORDER BY total DESC;
"""

FALSE_POSITIVE_TREND = """
SELECT
    DATE_TRUNC('day', created_at)       AS day,
    COUNT(*) FILTER (
        WHERE predicted = 'positive' AND ground_truth = 'negative'
    )                                   AS false_positives,
    COUNT(*)                            AS total_labelled,
    ROUND(
        COUNT(*) FILTER (
            WHERE predicted = 'positive' AND ground_truth = 'negative'
        )::numeric / NULLIF(COUNT(*), 0),
    4)                                  AS false_positive_rate
FROM decisions
WHERE ground_truth IS NOT NULL
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY day
ORDER BY day;
"""

REVERSAL_RATE_BY_CATEGORY = """
SELECT
    category,
    COUNT(*)                            AS total_decisions,
    SUM(reversed::int)                  AS total_reversals,
    ROUND(AVG(reversed::int)::numeric, 4) AS reversal_rate,
    ROUND(AVG(risk_score)::numeric, 4)  AS avg_risk_score
FROM decisions
GROUP BY category
ORDER BY reversal_rate DESC;
"""

QUALITY_SNAPSHOT_TREND = """
SELECT
    snapshot_at                         AS time,
    precision,
    recall,
    f1,
    false_positive_rate,
    false_negative_rate,
    escalation_rate,
    reversal_rate
FROM quality_snapshots
WHERE snapshot_at >= %(from_ts)s
  AND snapshot_at <= %(to_ts)s
ORDER BY snapshot_at;
"""

REVIEWER_AGREEMENT_BY_GROUP = """
SELECT
    reviewer_group,
    COUNT(*)                            AS total_reviews,
    ROUND(AVG(agreement_score)::numeric, 4)    AS avg_agreement,
    ROUND(STDDEV(agreement_score)::numeric, 4) AS stddev_agreement,
    MIN(agreement_score)                AS min_agreement,
    MAX(agreement_score)                AS max_agreement
FROM reviews
GROUP BY reviewer_group
ORDER BY avg_agreement DESC;
"""

# ── Trend / Drift ─────────────────────────────────────────────────────────

CATEGORY_DRIFT = """
WITH baseline AS (
    SELECT
        category,
        AVG(risk_score)     AS baseline_avg_score,
        COUNT(*)            AS baseline_count
    FROM decisions
    WHERE created_at BETWEEN NOW() - INTERVAL '14 days'
                         AND NOW() - INTERVAL '7 days'
    GROUP BY category
),
recent AS (
    SELECT
        category,
        AVG(risk_score)     AS recent_avg_score,
        COUNT(*)            AS recent_count
    FROM decisions
    WHERE created_at >= NOW() - INTERVAL '7 days'
    GROUP BY category
)
SELECT
    b.category,
    b.baseline_avg_score,
    b.baseline_count,
    r.recent_avg_score,
    r.recent_count,
    ROUND((r.recent_avg_score - b.baseline_avg_score)::numeric, 4) AS score_delta
FROM baseline b
JOIN recent r USING (category)
ORDER BY ABS(r.recent_avg_score - b.baseline_avg_score) DESC;
"""

EMERGING_FAILURE_CATEGORIES = """
WITH early_window AS (
    SELECT
        category,
        COUNT(*)            AS early_count
    FROM decisions
    WHERE created_at BETWEEN NOW() - INTERVAL '14 days'
                         AND NOW() - INTERVAL '7 days'
    GROUP BY category
),
recent_window AS (
    SELECT
        category,
        COUNT(*)            AS recent_count
    FROM decisions
    WHERE created_at >= NOW() - INTERVAL '7 days'
    GROUP BY category
),
totals AS (
    SELECT
        (SELECT COUNT(*) FROM decisions
         WHERE created_at BETWEEN NOW() - INTERVAL '14 days'
                              AND NOW() - INTERVAL '7 days')   AS early_total,
        (SELECT COUNT(*) FROM decisions
         WHERE created_at >= NOW() - INTERVAL '7 days')        AS recent_total
)
SELECT
    r.category,
    ROUND(r.recent_count::numeric / NULLIF(t.recent_total, 0), 4) AS recent_rate,
    ROUND(COALESCE(e.early_count, 0)::numeric /
          NULLIF(t.early_total, 0), 4)                             AS early_rate,
    ROUND(
        (r.recent_count::numeric / NULLIF(t.recent_total, 0)) -
        (COALESCE(e.early_count, 0)::numeric / NULLIF(t.early_total, 0)),
    4)                                                             AS delta
FROM recent_window r
LEFT JOIN early_window e USING (category),
totals t
WHERE (r.recent_count::numeric / NULLIF(t.recent_total, 0)) -
      (COALESCE(e.early_count, 0)::numeric / NULLIF(t.early_total, 0)) > 0.05
ORDER BY delta DESC;
"""

RISK_SCORE_DISTRIBUTION = """
SELECT
    DATE_TRUNC('day', created_at)       AS day,
    ROUND(AVG(risk_score)::numeric, 4)  AS avg_score,
    ROUND(
        PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY risk_score)::numeric,
    4)                                  AS p95_score,
    ROUND(
        PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY risk_score)::numeric,
    4)                                  AS p50_score
FROM decisions
WHERE created_at >= %(from_ts)s
  AND created_at <= %(to_ts)s
GROUP BY day
ORDER BY day;
"""

PRIORITY_DISTRIBUTION_SHIFT = """
SELECT
    DATE_TRUNC('day', created_at)       AS day,
    COUNT(*) FILTER (WHERE tier = 'automated') AS automated,
    COUNT(*) FILTER (WHERE tier = 'standard')  AS standard,
    COUNT(*) FILTER (WHERE tier = 'expert')    AS expert
FROM decisions
WHERE created_at >= %(from_ts)s
  AND created_at <= %(to_ts)s
GROUP BY day
ORDER BY day;
"""

# ── RCA ───────────────────────────────────────────────────────────────────

RCA_FAILURE_MODES = """
SELECT
    failure_type,
    category,
    COUNT(*)                            AS count,
    ROUND(AVG(risk_score)::numeric, 4)  AS avg_risk_score,
    MIN(created_at)                     AS first_seen,
    MAX(created_at)                     AS last_seen
FROM rca_failures
WHERE created_at >= %(from_ts)s
GROUP BY failure_type, category
ORDER BY count DESC;
"""

RCA_SIGNAL_MEANS = """
SELECT
    failure_type,
    ROUND(AVG((signals -> 'ml'     ->> 'risk_probability')::numeric), 4) AS avg_ml_score,
    ROUND(AVG((signals -> 'rule'   ->> 'risk_probability')::numeric), 4) AS avg_rule_score,
    ROUND(AVG(
        (signals -> 'heuristic' -> 'signals' ->> 'spam_patterns')::numeric
    ), 4)                                                                  AS avg_spam_signal,
    COUNT(*)                                                               AS total
FROM rca_failures
WHERE created_at >= %(from_ts)s
GROUP BY failure_type
ORDER BY total DESC;
"""

RCA_TOP_DISAGREEING_REVIEWERS = """
SELECT
    reviewer_id,
    COUNT(*)                            AS total_failures,
    COUNT(*) FILTER (
        WHERE failure_type = 'disagreement'
    )                                   AS disagreements,
    ROUND(
        COUNT(*) FILTER (WHERE failure_type = 'disagreement')::numeric /
        NULLIF(COUNT(*), 0),
    4)                                  AS disagreement_rate
FROM rca_failures
WHERE reviewer_id IS NOT NULL
GROUP BY reviewer_id
ORDER BY disagreement_rate DESC
LIMIT %(limit)s;
"""

# ── Experiments ───────────────────────────────────────────────────────────

EXPERIMENT_RESULTS_SUMMARY = """
SELECT
    e.experiment_id,
    e.name,
    e.status,
    o.variant,
    COUNT(*)                                               AS observations,
    ROUND(AVG((o.metrics ->> %(metric)s)::numeric), 4)    AS mean_metric,
    ROUND(STDDEV((o.metrics ->> %(metric)s)::numeric), 4) AS std_metric,
    MIN((o.metrics ->> %(metric)s)::numeric)               AS min_metric,
    MAX((o.metrics ->> %(metric)s)::numeric)               AS max_metric
FROM experiments e
JOIN experiment_observations o USING (experiment_id)
WHERE e.experiment_id = %(experiment_id)s
GROUP BY e.experiment_id, e.name, e.status, o.variant
ORDER BY mean_metric DESC;
"""

ACTIVE_EXPERIMENTS = """
SELECT
    experiment_id,
    name,
    status,
    variants,
    traffic_split,
    started_at,
    EXTRACT(EPOCH FROM (NOW() - started_at)) / 3600 AS running_hours
FROM experiments
WHERE status = 'running'
ORDER BY started_at;
"""