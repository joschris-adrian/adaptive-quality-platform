# These queries run against PostgreSQL via psycopg2 or SQLAlchemy.
# Each returns rows suitable for dashboard rendering or further analysis.

REVIEWER_AGREEMENT = """
SELECT
    reviewer_group,
    COUNT(*)                            AS total_reviews,
    AVG(agreement_score)                AS avg_agreement,
    STDDEV(agreement_score)             AS stddev_agreement,
    MIN(agreement_score)                AS min_agreement,
    MAX(agreement_score)                AS max_agreement
FROM reviews
GROUP BY reviewer_group
ORDER BY avg_agreement DESC;
"""

REVERSAL_RATE_BY_CATEGORY = """
SELECT
    category,
    COUNT(*)                            AS total_decisions,
    SUM(reversed::int)                  AS total_reversals,
    AVG(reversed::int)                  AS reversal_rate,
    AVG(risk_score)                     AS avg_risk_score
FROM decisions
GROUP BY category
ORDER BY reversal_rate DESC;
"""

PRECISION_RECALL_BY_TIER = """
SELECT
    tier,
    COUNT(*) FILTER (WHERE predicted = 'positive' AND ground_truth = 'positive') AS tp,
    COUNT(*) FILTER (WHERE predicted = 'positive' AND ground_truth = 'negative') AS fp,
    COUNT(*) FILTER (WHERE predicted = 'negative' AND ground_truth = 'negative') AS tn,
    COUNT(*) FILTER (WHERE predicted = 'negative' AND ground_truth = 'positive') AS fn,
    ROUND(
        COUNT(*) FILTER (WHERE predicted = 'positive' AND ground_truth = 'positive')::numeric /
        NULLIF(COUNT(*) FILTER (WHERE predicted = 'positive'), 0), 4
    ) AS precision,
    ROUND(
        COUNT(*) FILTER (WHERE predicted = 'positive' AND ground_truth = 'positive')::numeric /
        NULLIF(
            COUNT(*) FILTER (WHERE predicted = 'positive' AND ground_truth = 'positive') +
            COUNT(*) FILTER (WHERE predicted = 'negative' AND ground_truth = 'positive'), 0
        ), 4
    ) AS recall
FROM decisions
WHERE ground_truth IS NOT NULL
GROUP BY tier
ORDER BY tier;
"""

ESCALATION_RATE_OVER_TIME = """
SELECT
    DATE_TRUNC('hour', created_at)      AS hour,
    COUNT(*)                            AS total,
    SUM(escalated::int)                 AS escalated,
    ROUND(AVG(escalated::int), 4)       AS escalation_rate
FROM decisions
WHERE created_at >= NOW() - INTERVAL '7 days'
GROUP BY hour
ORDER BY hour;
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
        )::numeric / NULLIF(COUNT(*), 0), 4
    )                                   AS false_positive_rate
FROM decisions
WHERE ground_truth IS NOT NULL
  AND created_at >= NOW() - INTERVAL '30 days'
GROUP BY day
ORDER BY day;
"""

QUEUE_BACKLOG_BY_TIER = """
SELECT
    tier,
    COUNT(*) FILTER (WHERE reviewed_at IS NULL)     AS pending,
    COUNT(*) FILTER (WHERE reviewed_at IS NOT NULL) AS completed,
    AVG(
        EXTRACT(EPOCH FROM (reviewed_at - created_at)) / 60
    ) FILTER (WHERE reviewed_at IS NOT NULL)        AS avg_review_minutes,
    MAX(
        EXTRACT(EPOCH FROM (NOW() - created_at)) / 60
    ) FILTER (WHERE reviewed_at IS NULL)            AS oldest_pending_minutes
FROM decisions
GROUP BY tier
ORDER BY pending DESC;
"""

CATEGORY_DRIFT = """
WITH baseline AS (
    SELECT
        category,
        AVG(risk_score) AS baseline_avg_score
    FROM decisions
    WHERE created_at BETWEEN NOW() - INTERVAL '14 days' AND NOW() - INTERVAL '7 days'
    GROUP BY category
),
recent AS (
    SELECT
        category,
        AVG(risk_score) AS recent_avg_score
    FROM decisions
    WHERE created_at >= NOW() - INTERVAL '7 days'
    GROUP BY category
)
SELECT
    b.category,
    b.baseline_avg_score,
    r.recent_avg_score,
    ROUND((r.recent_avg_score - b.baseline_avg_score)::numeric, 4) AS score_delta
FROM baseline b
JOIN recent r USING (category)
ORDER BY ABS(r.recent_avg_score - b.baseline_avg_score) DESC;
"""