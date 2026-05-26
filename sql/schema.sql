-- ── decisions ──────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS decisions (
    id              BIGSERIAL PRIMARY KEY,
    event_id        UUID         NOT NULL UNIQUE,
    tier            VARCHAR(20)  NOT NULL,
    category        VARCHAR(50)  NOT NULL,
    predicted       VARCHAR(10)  NOT NULL CHECK (predicted IN ('positive', 'negative')),
    ground_truth    VARCHAR(10)           CHECK (ground_truth IN ('positive', 'negative')),
    risk_score      NUMERIC(6,4) NOT NULL DEFAULT 0.0,
    reviewer_id     VARCHAR(100),
    escalated       BOOLEAN      NOT NULL DEFAULT FALSE,
    reversed        BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    reviewed_at     TIMESTAMPTZ
);

-- ── reviews ────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviews (
    id              BIGSERIAL PRIMARY KEY,
    event_id        UUID         NOT NULL REFERENCES decisions(event_id),
    reviewer_id     VARCHAR(100) NOT NULL,
    reviewer_group  VARCHAR(50)  NOT NULL,
    decision        VARCHAR(10)  NOT NULL,
    agreement_score NUMERIC(4,3),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── quality_snapshots ──────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS quality_snapshots (
    id                  BIGSERIAL PRIMARY KEY,
    snapshot_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    total_decisions     INT          NOT NULL,
    labelled_count      INT          NOT NULL,
    precision           NUMERIC(6,4),
    recall              NUMERIC(6,4),
    f1                  NUMERIC(6,4),
    false_positive_rate NUMERIC(6,4),
    false_negative_rate NUMERIC(6,4),
    escalation_rate     NUMERIC(6,4),
    reversal_rate       NUMERIC(6,4)
);

-- ── rca_failures ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS rca_failures (
    id              BIGSERIAL PRIMARY KEY,
    event_id        UUID         NOT NULL,
    tier            VARCHAR(20)  NOT NULL,
    category        VARCHAR(50)  NOT NULL,
    failure_type    VARCHAR(30)  NOT NULL
                    CHECK (failure_type IN
                        ('false_positive','false_negative','reversal','disagreement')),
    risk_score      NUMERIC(6,4) NOT NULL,
    signals         JSONB        NOT NULL DEFAULT '{}',
    reviewer_id     VARCHAR(100),
    metadata        JSONB        NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── experiments ───────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS experiments (
    id              BIGSERIAL PRIMARY KEY,
    experiment_id   UUID         NOT NULL UNIQUE DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    description     TEXT,
    variants        JSONB        NOT NULL,
    metrics         JSONB        NOT NULL,
    traffic_split   JSONB        NOT NULL,
    status          VARCHAR(20)  NOT NULL DEFAULT 'draft'
                    CHECK (status IN ('draft','running','paused','completed')),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    metadata        JSONB        NOT NULL DEFAULT '{}'
);

-- ── experiment_observations ───────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS experiment_observations (
    id              BIGSERIAL PRIMARY KEY,
    experiment_id   UUID         NOT NULL REFERENCES experiments(experiment_id),
    variant         VARCHAR(100) NOT NULL,
    event_id        VARCHAR(200) NOT NULL,
    metrics         JSONB        NOT NULL DEFAULT '{}',
    observed_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- ── indexes ───────────────────────────────────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_decisions_category
    ON decisions(category);
CREATE INDEX IF NOT EXISTS idx_decisions_tier
    ON decisions(tier);
CREATE INDEX IF NOT EXISTS idx_decisions_created_at
    ON decisions(created_at);
CREATE INDEX IF NOT EXISTS idx_decisions_ground_truth
    ON decisions(ground_truth) WHERE ground_truth IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_decisions_risk_score
    ON decisions(risk_score);
CREATE INDEX IF NOT EXISTS idx_decisions_reversed
    ON decisions(reversed) WHERE reversed = TRUE;
CREATE INDEX IF NOT EXISTS idx_reviews_reviewer_group
    ON reviews(reviewer_group);
CREATE INDEX IF NOT EXISTS idx_reviews_event_id
    ON reviews(event_id);
CREATE INDEX IF NOT EXISTS idx_snapshots_at
    ON quality_snapshots(snapshot_at);
CREATE INDEX IF NOT EXISTS idx_rca_failures_category
    ON rca_failures(category);
CREATE INDEX IF NOT EXISTS idx_rca_failures_type
    ON rca_failures(failure_type);
CREATE INDEX IF NOT EXISTS idx_rca_failures_created_at
    ON rca_failures(created_at);
CREATE INDEX IF NOT EXISTS idx_exp_observations_experiment
    ON experiment_observations(experiment_id);
CREATE INDEX IF NOT EXISTS idx_exp_observations_variant
    ON experiment_observations(variant);