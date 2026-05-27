# Adaptive Risk & Quality Analytics Platform

A scalable analytics and decision-support platform that monitors the quality
of automated decisions, prioritises high-risk events, and optimises human
review workflows under operational and cost constraints.

---

## Table of Contents

1. [Problem Statement](#1-problem-statement)
2. [Architecture](#2-architecture)
3. [Project Structure](#3-project-structure)
4. [Quickstart](#4-quickstart)
5. [Event Ingestion Layer](#5-event-ingestion-layer)
6. [Automated Detection Pipeline](#6-automated-detection-pipeline)
7. [Risk Scoring Framework](#7-risk-scoring-framework)
8. [Hybrid Human-AI Workflow Engine](#8-hybrid-human-ai-workflow-engine)
9. [Quality vs Cost Optimisation](#9-quality-vs-cost-optimisation)
10. [Quality Analytics Engine](#10-quality-analytics-engine)
11. [Root Cause Analysis Engine](#11-root-cause-analysis-engine)
12. [Experimentation Framework](#12-experimentation-framework)
13. [Dashboards and Reporting](#13-dashboards-and-reporting)
14. [Data and Analytics Layer](#14-data-and-analytics-layer)
15. [Distributed System Design](#15-distributed-system-design)
16. [Hardware-Aware Optimisation](#16-hardware-aware-optimisation)
17. [Evaluation Metrics](#17-evaluation-metrics)
18. [Key Experiments](#18-key-experiments)
19. [Demo](#19-demo)
20. [Operational Tradeoffs](#20-operational-tradeoffs)
21. [Benchmarking Results](#21-benchmarking-results)
22. [Scaling Experiments](#22-scaling-experiments)
23. [Lessons Learned](#23-lessons-learned)
24. [Next Steps](#24-Next-Steps)

---

## 1. Problem Statement

Modern platforms increasingly rely on a combination of automated classifiers,
human reviewers, escalation workflows and continuously updated policies. This
creates four operational problems:

- **Decision quality drifts** as event distributions shift over time
- **New failure patterns emerge** that existing rules and models do not cover
- **Human review capacity is limited** and expensive to scale
- **False positives and false negatives have asymmetric costs** — a missed
  fraud event costs far more than an unnecessary review

This platform addresses all four problems by building a unified system that:

1. Ingests events from multiple source systems in real time
2. Runs automated detection across ML, rule-based, and heuristic detectors
3. Scores risk using a Likelihood × Severity × Exposure framework
4. Routes decisions dynamically between automated systems and human reviewers
5. Tracks quality metrics continuously and detects drift
6. Performs root cause analysis on failure patterns
7. Supports controlled experiments to validate policy and threshold changes
8. Optimises routing strategy under operational and cost constraints

---

## 2. Architecture
Event Stream → Detection Pipeline → Risk Scoring → Routing Engine
↓
Quality Analytics Engine
↓
RCA + Trend Detection + Reporting

### Data flow
┌─────────────────────────────────────────────────────────────┐
│                     Event Sources                           │
│   User actions │ Moderation decisions │ Transactions        │
│   Review outcomes │ Operational alerts                      │
└───────────────────────────┬─────────────────────────────────┘
                            │ POST /api/v1/ingest
                            ▼
                    ┌───────────────┐
                    │  FastAPI API  │  validate + enrich
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Kafka Broker  │  raw-events
                    └───────┬───────┘
                            │
              ┌─────────────┼──────────────┐
              ▼             ▼              ▼
        ┌──────────┐  ┌──────────┐  ┌──────────┐
        │    ML    │  │  Rules   │  │Heuristics│  Detection
        │Classifier│  │ Engine   │  │ Detector │  Pipeline
        └────┬─────┘  └────┬─────┘  └────┬─────┘
              └─────────────┼─────────────┘
                            │ scored-events
                            ▼
                    ┌───────────────┐
                    │  Risk Scorer  │  Likelihood × Severity × Exposure
                    └───────┬───────┘
                            │ review-queue
                            ▼
                    ┌───────────────┐
                    │Routing Engine │  policy + capacity
                    └───────┬───────┘
                            │
          ┌─────────────────┼──────────────────┐
          ▼                 ▼                  ▼
    auto-actioned    standard-review-*    expert-review-*

### Technology stack

| Component         | Technology                        |
|-------------------|-----------------------------------|
| API               | FastAPI + uvicorn                 |
| Message broker    | Apache Kafka (KRaft mode)         |
| Database          | PostgreSQL 16                     |
| Dashboards        | Grafana 10 + Prometheus           |
| Orchestration     | Kubernetes + KEDA                 |
| Language          | Python 3.13                       |
| Testing           | pytest + pytest-asyncio           |
| Experiment tracking  | MLflow 2.x                        |

---

## 3. Project Structure
adaptive-quality-platform/
│
├── .env.example
├── .gitignore
├── pyproject.toml
├── conftest.py
├── run.py                        ← cross-platform task runner (Windows/Mac/Linux)
│
├── api/
│   ├── main.py
│   ├── schemas.py
│   └── routes/
│       └── ingest.py
│
├── services/
│   ├── detection/
│   │   ├── pipeline.py
│   │   ├── classifier.py
│   │   ├── rules.py
│   │   ├── heuristics.py
│   │   ├── consumer.py
│   │   └── output_schema.py
│   │
│   ├── risk_scoring/
│   │   ├── scorer.py
│   │   ├── weights.py
│   │   ├── weights.yaml
│   │   ├── consumer.py
│   │   └── output_schema.py
│   │
│   ├── routing/
│   │   ├── engine.py
│   │   ├── policies.py
│   │   ├── capacity.py
│   │   ├── consumer.py
│   │   └── output_schema.py
│   │
│   ├── analytics/
│   │   ├── metrics.py
│   │   ├── quality.py
│   │   ├── cost.py
│   │   ├── comparison.py
│   │   ├── reporter.py
│   │   ├── experimentation.py
│   │   ├── evaluation.py
│   │   ├── consumer.py
│   │   ├── db.py
│   │   └── repository.py
│   │
│   ├── mlflow/
│   │   ├── __init__.py
│   │   ├── tracking.py
│   │   └── registry.py
│   │
│   └── rca/
│       ├── root_cause.py
│       ├── similarity.py
│       └── consumer.py
│
├── dashboards/
│   ├── snapshot_writer.py
│   ├── report_generator.py
│   └── grafana/
│       ├── docker-compose.yml
│       ├── prometheus.yml
│       ├── provisioning/
│       │   ├── datasources/
│       │   │   ├── postgres.yaml
│       │   │   └── prometheus.yaml
│       │   └── dashboards/
│       │       └── provider.yaml
│       └── dashboards/
│           ├── operational.json
│           ├── quality.json
│           └── trends.json
│
├── sql/
│   ├── schema.sql
│   └── queries.py
│
├── kafka/
│   ├── consumer_base.py
│   └── topics.yaml
│
├── k8s/
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── postgres.yaml
│   ├── kafka.yaml
│   ├── kafka-init-job.yaml
│   ├── detection.yaml
│   ├── risk-scoring.yaml
│   ├── routing.yaml
│   ├── analytics.yaml
│   ├── api.yaml
│   ├── mlflow.yaml
│   ├── snapshot-cronjob.yaml
│   ├── keda-scaledobjects.yaml
│   └── Dockerfile
│
├── scripts/
│   ├── synthetic_data_generator.py
│   ├── seed_database.py              
│   ├── simulate_scoring.py
│   ├── run_comparison.py
│   ├── run_rca.py
│   ├── train_classifier.py
│   ├── run_report.py
│   ├── run_ab_experiment.py
│   ├── run_platform_experiments.py
│   └── scaling_analysis.py
│
└── tests/
    ├── test_detection_pipeline.py
    ├── test_classifier.py
    ├── test_rule_engine.py
    ├── test_heuristics.py
    ├── test_risk_scorer.py
    ├── test_routing_engine.py
    ├── test_quality_cost.py
    ├── test_quality_analytics.py
    ├── test_rca_engine.py
    ├── test_experimentation.py
    ├── test_evaluation.py
    ├── test_snapshot_writer.py
    ├── test_report_generator.py
    ├── test_repository.py
    ├── test_scaling_analysis.py
    ├── test_run_ab_experiment.py
    ├── test_run_platform_experiments.py
    ├── test_run_rca.py
    ├── test_synthetic_data_generator.py
    ├── test_seed_database.py  
    ├── test_mlflow_tracking.py
    ├── test_mlflow_registry.py
    ├── test_train_classifier.py
    ├── test_mlflow_tracking_integration.py
    ├── test_run_rca_script.py
    ├── test_run_ab_experiment_script.py       
    └── test_run_py.py
    ---

## 4. Quickstart

### Prerequisites

- Python 3.13
- Docker Desktop
- Git

### Setup

```bash
# clone and enter
git clone https://github.com/yourname/adaptive-quality-platform.git
cd adaptive-quality-platform

# copy and fill in secrets (edit POSTGRES_PASSWORD and GRAFANA_PASSWORD)
cp .env.example .env

# install dependencies
pip install -r requirements.txt

# start Grafana + Postgres + Prometheus + Kafka
python run.py up

# initialise the database schema
python run.py init-db

python run.py mlflow-up      # start MLflow tracking server (http://localhost:5000)
python run.py mlflow-down    # stop MLflow server
python run.py train          # train classifier and log to MLflow

# run all tests
python run.py test

# seed the pipeline with 500 synthetic events (requires API running)
# terminal 1
python run.py api
# terminal 2
python run.py seed

# run benchmarks
python run.py bench
```

### Task runner

All commands go through `run.py` — a pure Python script that works on
Windows, Mac, and Linux with no additional tools required:

```bash
python run.py help        # list all commands
python run.py up          # start Docker stack
python run.py down        # stop Docker stack
python run.py api         # start FastAPI server (keep terminal open)
python run.py seed        # send 500 synthetic events to the API
python run.py test        # run all tests
python run.py coverage    # tests with coverage report
python run.py bench       # scaling benchmarks
```

### requirements.txt

```
fastapi
uvicorn
kafka-python
psycopg2-binary
pydantic
pyyaml
joblib
numpy
pytest
pytest-asyncio
pytest-cov
httpx
```
## 5. Event Ingestion Layer

Events enter the platform via a FastAPI endpoint and are published to Kafka.

**Supported event types:**

| Type                  | Kafka topic    |
|-----------------------|----------------|
| `user_action`         | `raw-events`   |
| `moderation_decision` | `raw-events`   |
| `transaction`         | `raw-events`   |
| `operational_alert`   | `raw-events`   |
| `review_outcome`      | `review-queue` |

**Validation:**

Schema-level (Pydantic — hard rejection, returns 422):
- `event_type` must be one of the five allowed literals
- `source_system` must not be blank
- `payload` must not be empty
- `timestamp` must not be older than 24 hours

Business-level (soft warnings returned in response body):
- `user_action` events should include `user_id` in payload
- `transaction` events should include `amount` in payload
- `risk_hint` must be numeric and within `[0.0, 1.0]`

**Enrichment** — derived fields added before publishing to Kafka:

| Field             | Derived from                                              |
|-------------------|-----------------------------------------------------------|
| `risk_hint`       | Extracted from payload, clamped to `[0, 1]`              |
| `user_id`         | Extracted from payload                                    |
| `is_high_value`   | True if category is fraud/policy_violation, amount > $10k, or risk_hint ≥ 0.90 |
| `normalised_type` | Canonical category: behavioural, financial, moderation, review, operational |
| `latency_ms`      | Enrichment pipeline latency in milliseconds               |
| `ingestion_ts`    | UTC timestamp when the API received the event             |
| `schema_version`  | Always `"1.0"`                                            |

**Health endpoints:**

| Endpoint       | Purpose                          |
|----------------|----------------------------------|
| `GET /healthz` | Liveness — always returns 200    |
| `GET /readyz`  | Readiness — checks Kafka is reachable |

**Key design decisions:**

- `KafkaProducer` is lazy — created on first request, not at import
  time, so the API starts without a Kafka connection
- `KAFKA_BOOTSTRAP_SERVERS` env var defaults to `localhost:9092` for
  local dev; set to `kafka:9092` in Docker/Kubernetes via ConfigMap
- `acks="all"` ensures durability at the cost of slightly higher latency
- `enable_auto_commit=False` on all consumers prevents silent data loss
- Failed messages route to `dlq-events` (30-day retention) for replay

**Seed synthetic events:**

```bash
# terminal 1 — start the API
python run.py api

# terminal 2 — send 500 events
python run.py seed
```

Seeding sends 500 randomly generated events covering all event types,
source systems, and risk levels. It exists purely for local development
and demos — in production, real user actions flow in naturally.

---

## 6. Automated Detection Pipeline

Each event passes through three detectors running concurrently via
`asyncio.gather`. Results are aggregated by weighted combination.

**Detectors:**

| Detector       | Method                        | Weight |
|----------------|-------------------------------|--------|
| ML classifier  | Probability score 0–1         | 0.50   |
| Rule engine    | Threshold and blocklist checks | 0.30   |
| Heuristics     | Spam patterns, time anomalies  | 0.20   |

**Aggregation:**
final_score = ml_score × 0.5 + rule_score × 0.3 + heuristic_score × 0.2

A 0.1 agreement bonus is added when all three detectors score above 0.5,
capped at 1.0.

**Output schema:**

```json
{
  "event_id": "evt-001",
  "risk_probability": 0.87,
  "category": "policy_violation",
  "signals": {
    "ml":        {"risk_probability": 0.91, "category": "fraud"},
    "rule":      {"risk_probability": 1.00, "rules_triggered": ["blocklisted_user"]},
    "heuristic": {"risk_probability": 0.60, "signals": {"spam_patterns": 0.7}}
  }
}
```

---

## 7. Risk Scoring Framework

Risk is computed as a product of three normalised components:
Risk Score = Likelihood × Severity × Exposure

| Component   | Source                                      |
|-------------|---------------------------------------------|
| Likelihood  | Aggregated detector probability + agreement bonus |
| Severity    | Category weight from `weights.yaml`         |
| Exposure    | Event type and source system weights        |

A `x^0.75` soft curve is applied after multiplication to spread
mid-range scores and improve priority separation.

**Priority bands:**

| Score       | Priority |
|-------------|----------|
| ≥ 0.85      | Critical |
| 0.65–0.84   | High     |
| 0.40–0.64   | Medium   |
| < 0.40      | Low      |

Weights are loaded from `weights.yaml` with a 60-second TTL cache,
enabling hot-reload without redeployment.

**Tune weights without redeploying:**

```bash
# edit weights
vim services/risk_scoring/weights.yaml

# in k8s: update the ConfigMap
kubectl edit configmap risk-scoring-weights -n adaptive-quality
# pods pick up the change within 60 seconds
```

---

## 8. Hybrid Human-AI Workflow Engine

The routing engine applies a three-layer decision stack:
Score threshold override
↓
Category override
↓
Priority map

**Routing table:**

| Priority | Default action    | SLA     |
|----------|-------------------|---------|
| Critical | Escalated review  | 15 min  |
| High     | Escalated review  | 15 min  |
| Medium   | Standard review   | 60 min  |
| Low      | Auto-action       | None    |

**Overrides:**

- Score < 0.25 → always auto-action regardless of priority
- Score ≥ 0.80 → always escalate regardless of priority
- Category `fraud` or `policy_violation` → always escalate

**Capacity management:**

When a tier queue is saturated, events are downgraded one tier.
Critical events are never downgraded — they are held with action `hold`
until capacity frees up.

escalated_review (full) → standard_review
standard_review  (full) → auto_action
critical + expert full  → hold

---

## 9. Quality vs Cost Optimisation

Four routing strategies are compared across quality and cost dimensions:

| Strategy              | Auto% | Std%  | Expert% | Quality | Cost (10k events) |
|-----------------------|-------|-------|---------|---------|-------------------|
| `automation_only`     | 100%  | 0%    | 0%      | 0.72    | ~$10              |
| `hybrid_balanced`     | 70%   | 22%   | 8%      | 0.81    | ~$760             |
| `hybrid_quality_first`| 40%   | 35%   | 25%     | 0.87    | ~$1,900           |
| `human_heavy`         | 10%   | 60%   | 30%     | 0.92    | ~$4,900           |

The recommender enforces a quality floor of 0.80 before optimising for
efficiency ratio (quality per dollar), preventing the system from
recommending automation-only purely on cost.

```bash
python run.py run-comparison
```

---

## 10. Quality Analytics Engine

Tracks decision quality continuously across three dimensions:

**Metrics tracked:**

- Precision, Recall, F1
- False positive rate, False negative rate
- Escalation rate
- Reversal rate
- Reviewer agreement rate

All metrics are computed per-tier and per-category in addition to global
aggregates. Snapshots are written to PostgreSQL every 15 minutes and
surfaced in the quality Grafana dashboard.

**Drift detection:**

Compares the first N labelled records against the most recent N.
A delta > 5% in precision or recall triggers `drift_detected`.

```python
from services.analytics.metrics import QualityAnalyticsEngine

engine = QualityAnalyticsEngine()
report = engine.drift_report(window_size=100)
# {"status": "drift_detected", "precision_delta": -0.08, ...}
```

---

## 11. Root Cause Analysis Engine

Identifies why decisions fail and surfaces emerging patterns.

**Failure types tracked:**

| Type             | Definition                                    |
|------------------|-----------------------------------------------|
| `false_positive` | Predicted positive, ground truth negative     |
| `false_negative` | Predicted negative, ground truth positive     |
| `reversal`       | A later reviewer overturned the decision      |
| `disagreement`   | Reviewers disagreed on the same event         |

**Clustering strategies:**

- `category_x_type` — groups by what failed and why
- `tier_x_type` — groups by where in the pipeline failure occurred
- `risk_band_x_type` — groups by score range
- Cosine similarity on signal vectors for nearest-neighbour grouping

**Run RCA:**

```bash
python scripts/run_rca.py
```

**Example output:**

```json
{
  "status": "drift_detected",
  "emerging_categories": [
    {"category": "new_attack_vector", "early_rate": 0.0, "recent_rate": 0.32, "delta": 0.32}
  ],
  "top_cluster": "fraud::false_positive",
  "signal_correlation": {
    "ml.risk_probability": {"mean_on_failures": 0.68}
  }
}
```

---

## 12. Experimentation Framework

Supports four experiment types without code changes between runs.

**Experiment types:**

| Type                     | Class method                              |
|--------------------------|-------------------------------------------|
| A/B routing strategy     | `ExperimentEngine.create` + `assign`      |
| Threshold sensitivity    | `ExperimentEngine.threshold_experiment`   |
| Label quality comparison | `ExperimentEngine.label_quality_experiment` |
| Sampling strategy        | `ExperimentEngine.sampling_experiment`    |

**Assignment is deterministic** — the same `event_id` always maps to the
same variant so experiments are reproducible from logs alone.

**Winner selection** uses a lower-is-better list for cost metrics
(`cost`, `reversal_rate`, `false_positive_rate`, `latency_ms`) and
higher-is-better for all others.

```bash
# run the A/B experiment demo
python scripts/run_ab_experiment.py
```

---

## 13. Dashboards and Reporting

Three Grafana dashboards are provisioned automatically on container start.

**Operational dashboard** (`operational.json`):

- Event volume per minute by tier
- Queue backlog by tier with threshold colouring
- Decision latency p50 / p95
- Oldest pending event
- Throughput (decisions/hour)
- Escalation rate over time

**Quality dashboard** (`quality.json`):

- Precision and recall time series
- Current precision / recall / F1 / reversal rate gauges
- Precision and recall breakdown by tier (table)
- Reversal rate by category (bar chart)

**Trend dashboard** (`trends.json`):

- False positive rate trend (30 days)
- Risk score distribution (avg + p95)
- Category drift — score delta vs baseline
- Emerging failure categories (table)
- Reviewer agreement trend
- Priority distribution shift (stacked area)

**Scheduled report:**

```bash
python scripts/run_report.py
# writes reports/report_YYYYMMDD_HHMMSS.json
```

**Start dashboards:**

```bash
python run.py up
# Grafana    → http://localhost:3000
# Prometheus → http://localhost:9090
```

---

## 14. Data and Analytics Layer

**PostgreSQL schema — five tables:**

| Table                     | Purpose                                  |
|---------------------------|------------------------------------------|
| `decisions`               | Every routing decision with outcome      |
| `reviews`                 | Individual reviewer actions              |
| `quality_snapshots`       | Periodic quality metric checkpoints      |
| `rca_failures`            | Failure records for RCA engine           |
| `experiments`             | Experiment definitions and status        |
| `experiment_observations` | Per-event metric observations            |

All named SQL queries live in `sql/queries.py` as module-level constants,
keeping query logic separate from Python and making them greppable and
independently testable.

The repository layer (`services/analytics/repository.py`) maps Python
dicts to SQL parameters and rows back to dicts. No business logic lives
in the repository — it is a pure translation layer.

---

## 15. Distributed System Design

Each service runs as an independent Kubernetes Deployment with its own
Kafka consumer group, HPA, and KEDA ScaledObject.

**Services and ports:**

| Service       | Port | Kafka topic consumed    | Kafka topic produced   |
|---------------|------|-------------------------|------------------------|
| API           | 8000 | —                       | `raw-events`           |
| Detection     | 8001 | `raw-events`            | `scored-events`        |
| Risk scoring  | 8002 | `scored-events`         | `review-queue`         |
| Routing       | 8003 | `review-queue`          | `expert-review-*` etc. |
| Analytics     | 8004 | `routed-decisions`      | —                      |

**Kafka topics:**

| Topic                  | Partitions | Retention |
|------------------------|------------|-----------|
| `raw-events`           | 6          | 7 days    |
| `scored-events`        | 6          | 7 days    |
| `review-queue`         | 3          | 7 days    |
| `auto-actioned-events` | 3          | 7 days    |
| `routed-decisions`     | 3          | 7 days    |
| `review-outcomes`      | 3          | 7 days    |
| `dlq-events`           | 2          | 30 days   |

**Autoscaling strategy:**

KEDA ScaledObjects scale each consumer deployment based on Kafka consumer
group lag rather than CPU, which is the correct signal for event-driven
workloads. CPU scaling only rises after the queue is already large —
lag-based scaling responds immediately.

| Service      | Min replicas | Max replicas | Lag threshold |
|--------------|-------------|--------------|---------------|
| Detection    | 2           | 10           | 500 messages  |
| Risk scoring | 2           | 8            | 300 messages  |
| Routing      | 2           | 6            | 100 messages  |

**Deploy to Kubernetes:**

```bash
python run.py k8s-up
python run.py k8s-status
```

---

## 16a. Hardware-Aware Optimisation

This section demonstrates throughput and latency tradeoffs achievable
without specialised hardware.

**Async batch inference:**

`asyncio.gather` runs all three detectors concurrently per event and all
events concurrently within a batch. Benchmarks show consistent speedup
over sequential processing.

**Batch size tuning:**

Detection throughput scales with batch size up to approximately 200 events,
after which gains flatten due to event-loop scheduling overhead.

| Batch size | Throughput (events/s) | Latency per event (ms) |
|------------|----------------------|------------------------|
| 1          | ~80                  | ~12.5                  |
| 10         | ~600                 | ~1.7                   |
| 50         | ~2,000               | ~0.5                   |
| 200        | ~4,500               | ~0.22                  |

**Consumer parallelism:**a local development environment. The async and
batching patterns demon

Kafka consumer groups allow horizontal scaling by replica count. KEDA
ScaledObjects autoscale based on topic lag — the practical equivalent of
accelerator-aware scheduling for this workload type.

GPU inference and multi-node benchmarks are excluded as they require
hardware not available in strated here apply directly to GPU-backed inference
servers such as Triton when the platform is deployed to cloud infrastructure.

```bash
python run.py bench
```

## 16b. MLflow Integration

MLflow tracks all experiments, model training runs, and drift snapshots persistently.

**Experiments logged:**

| Experiment              | Script                              | Metrics logged                          |
|-------------------------|-------------------------------------|-----------------------------------------|
| `platform-experiments`  | `run_platform_experiments.py`       | quality, cost, efficiency_ratio         |
| `threshold-sweep`       | `run_platform_experiments.py`       | quality, cost, auto_pct, threshold      |
| `ab-routing-strategy`   | `run_ab_experiment.py`              | precision, cost_per_event, reversal_rate|
| `drift-monitoring`      | `run_rca.py`                        | precision_delta, recall_delta, emerging_categories_count |
| `classifier-training`   | `train_classifier.py`               | precision, recall, f1                   |

**Model registry:**

The ML classifier is registered under `risk-classifier` and promoted through `Staging → Production`. The routing engine loads the `Production` version by stage name, not by hardcoded weights.

**Start MLflow:**

\```bash
python run.py mlflow-up
# MLflow UI → http://localhost:5000
\```

**Train and register the classifier:**

\```bash
python run.py train
\```

**New files added:**

| File                            | Purpose                                      |
|---------------------------------|----------------------------------------------|
| `services/mlflow/tracking.py`   | Thin wrapper around mlflow logging calls     |
| `services/mlflow/registry.py`   | Model registration and stage promotion       |
| `scripts/train_classifier.py`   | Train classifier, log to MLflow, register    |

---

## 17. Evaluation Metrics

Three metric categories are tracked and reportable independently.

**Quality metrics:**

| Metric               | Formula                           |
|----------------------|-----------------------------------|
| Precision            | TP / (TP + FP)                    |
| Recall               | TP / (TP + FN)                    |
| F1                   | 2 × P × R / (P + R)               |
| False positive rate  | FP / (FP + TN)                    |
| False negative rate  | FN / (FN + TP)                    |
| Accuracy             | (TP + TN) / Total                 |

Computed globally, per-tier, per-category, with macro and weighted averages.

**Operational metrics:**

| Metric                  | Definition                                  |
|-------------------------|---------------------------------------------|
| Queue latency p50/p95   | Decision review time percentiles            |
| Throughput              | Events processed per second                 |
| Resource utilisation    | Weighted CPU (60%) + memory (40%) composite |
| Queue backlog health    | Fill% + SLA breach → healthy/warning/critical |

**Business metrics:**

| Metric                      | Definition                                   |
|-----------------------------|----------------------------------------------|
| Cost per reviewed event      | Total cost / reviewed events                |
| High-risk capture rate       | Correctly escalated / total high-risk       |
| Escalation efficiency        | True positives / total escalated            |
| ROI                          | (Value captured − cost) / cost              |
| False negative business cost | FN count × cost per miss                    |

`EvaluationSuite.compare` scores two experiment arms with a weighted
combination of F1 (50%), high-risk capture rate (30%), and cost (20%).

---

## 18. Key Experiments

All four experiments run against the same pipeline with no code changes —
only routing strategy, threshold, or budget parameters differ.

| # | Experiment                              | Entry point                                         |
|---|-----------------------------------------|-----------------------------------------------------|
| 1 | Automation-only workflow                | `STRATEGIES["automation_only"]`                     |
| 2 | Hybrid human-AI routing                 | `STRATEGIES["hybrid_balanced"]`                     |
| 3 | Threshold adjustment under distribution shift | `ExperimentEngine.threshold_experiment()`     |
| 4 | Cost-aware prioritisation under capacity| `QualityCostComparator.cost_under_budget()`         |

```bash
python scripts/run_platform_experiments.py
```

**Example output:**
=================================================================
Experiments 1 & 2 — Strategy Comparison
Strategy                       Cost    Quality   Efficiency
automation_only               $10      0.7200    0.072000
hybrid_balanced               $760     0.8076    0.001063  ◄
hybrid_quality_first         $1,900    0.8700    0.000458
human_heavy                  $4,900    0.9200    0.000188
=================================================================
Experiment 3 — Threshold Sweep
Threshold       Cost    Quality   Auto%
  0.50     $4,500    0.8820     10%
  0.70     $1,200    0.8100     55%
  0.80       $760    0.8076     70%
  0.90       $200    0.7500     88%

=================================================================
Experiment 4 — Budget=$3,000
hybrid_quality_first       cost=$1,900  quality=0.8700
hybrid_balanced            cost=$760    quality=0.8076

---

## 19. Demo

### Step 1 — Start the stack

```bash
cp .env.example .env
python run.py up
python run.py init-db
python run.py ps
# grafana, postgres, prometheus, kafka should all be Up
```

### Step 2 — Seed events

```bash
# terminal 1
python run.py api
# wait for: INFO: Application startup complete.

# terminal 2
python run.py seed
# sends 500 synthetic events through the full ingestion pipeline
# each event is validated, enriched, and published to Kafka
```

### Step 2b — Seed the database for dashboards

If you want Grafana dashboards to show data without running the full
Kafka pipeline, seed PostgreSQL directly:

```bash
python run.py seed-db
# writes 500 decisions, 200 reviews, 50 quality snapshots, 100 RCA failures
# then refresh Grafana at http://localhost:3000
```

### Step 3 — Run the detection pipeline locally

```bash
python run.py simulate-scoring
```

### Step 4 — View dashboards

Open Grafana at `http://localhost:3000` (admin / password from `.env`).

- **Operational dashboard** — event volume, queue backlog, latency
- **Quality dashboard** — precision/recall gauges and trends
- **Trend dashboard** — drift analysis and emerging categories

### Step 5 — Run quality vs cost comparison

```bash
python run.py run-comparison
```

### Step 6 — Run the RCA engine

```bash
python run.py rca
```

### Step 7 — Run the A/B experiment

```bash
python run.py ab-experiment
```

### Step 8a — Run all four key experiments

```bash
python run.py platform-experiments
```

### Step 8b — View experiment results in MLflow

Open MLflow at `http://localhost:5000`.

- **platform-experiments** — strategy comparison and threshold sweep runs
- **ab-routing-strategy** — control vs treatment variant metrics
- **drift-monitoring** — RCA drift snapshots
- **classifier-training** — model versions with precision/recall/F1

### Step 9 — Generate a report

```bash
python run.py report
```

### Step 10 — Run benchmarks

```bash
python run.py bench
```

### Step 11 — Run tests

```bash
python run.py test
python run.py coverage
```

### Step 12 — Deploy to Kubernetes (optional)

```bash
python run.py k8s-up
python run.py k8s-status
python run.py k8s-logs --svc detection
```
---

## 20. Operational Tradeoffs

**Automation threshold:**
Lowering the escalation threshold from 0.80 to 0.65 increases human
review volume by ~40% and improves precision by ~8 percentage points.
Above 0.80, gains flatten while cost continues to rise linearly.

**Kafka consumer lag vs CPU scaling:**
CPU-based autoscaling reacts after queues are already large because CPU
only rises once processing is backlogged. Lag-based scaling via KEDA
reacts immediately when messages arrive faster than they are consumed.

**Agreement bonus in detection:**
The 0.1 agreement bonus when all three detectors agree above 0.5 improves
precision on high-confidence events at the cost of slightly lower recall
on edge cases where only one detector fires.

**DLQ retention (30 days vs 7 days):**
Failed messages need longer retention than successful ones because the
root cause often requires investigation before replay is possible.
30-day DLQ retention ensures replayability without excessive storage cost.

**Weights hot-reload:**
The 60-second TTL on `weights.yaml` allows threshold tuning in production
without a redeploy. The tradeoff is that all replicas of risk-scoring may
use different weights for up to 60 seconds after a change.

---

## 21. Benchmarking Results

All benchmarks run on a local machine (Python 3.13, no GPU).

**Detection pipeline (async batch):**

| Batch size | Throughput   | Latency/event |
|------------|-------------|---------------|
| 1          | ~80 ev/s    | ~12.5 ms      |
| 10         | ~600 ev/s   | ~1.7 ms       |
| 50         | ~2,000 ev/s | ~0.5 ms       |
| 200        | ~4,500 ev/s | ~0.22 ms      |

**Service throughput (sequential, no Kafka):**

| Service      | Throughput    |
|--------------|--------------|
| Risk scoring | ~18,500 ev/s |
| Routing      | ~22,000 ev/s |

**Cold start latency:**

| Component                      | Mean latency |
|--------------------------------|-------------|
| DetectionPipeline + RiskScorer + RoutingEngine | ~3 ms |

**Batch vs sequential speedup:** ~6x for 100-event batches.

---

## 22. Scaling Experiments

**Experiment: batch size vs throughput**

Throughput increases with batch size up to ~200 events. Beyond that,
`asyncio` scheduling overhead dominates and gains flatten. Optimal batch
size for this pipeline on local hardware is 100–200 events.

**Experiment: consumer replicas vs lag**

With a single detection replica consuming `raw-events` at 100 events/s
and producers at 500 events/s, lag grows at ~400 messages/minute. With
4 replicas, lag stabilises near zero. KEDA triggers a scale-up at 500
messages lag with a 30-second cooldown.

**Experiment: threshold vs cost/quality curve**

| Threshold | Auto% | Cost (10k) | Quality |
|-----------|-------|------------|---------|
| 0.50      | 10%   | ~$4,500    | 0.882   |
| 0.65      | 45%   | ~$2,100    | 0.850   |
| 0.75      | 62%   | ~$1,100    | 0.820   |
| 0.80      | 70%   | ~$760      | 0.808   |
| 0.90      | 88%   | ~$200      | 0.750   |

The inflection point is around 0.75–0.80: quality drops sharply below
0.75 while cost rises sharply above 0.80.

---

## 23. Lessons Learned

**Asymmetric costs require explicit modelling.**
Treating false positives and false negatives as equally bad leads to
suboptimal thresholds. Modelling cost per miss separately from cost per
false alarm allows the routing engine to make economically rational
decisions rather than optimising raw accuracy.

**Drift detection needs a baseline window, not a point-in-time snapshot.**
Comparing the most recent 50 records against a single snapshot is noisy.
Comparing two windows of equal size (early vs recent) is more stable and
catches gradual drift that point comparisons miss.

**Lag-based autoscaling outperforms CPU-based for consumer workloads.**
CPU scaling has a built-in delay: CPU only rises after the queue is
already large, meaning the scaleup happens after SLAs are already
breached. Lag-based scaling via KEDA responds to the actual signal.

**Hot-reloadable weights are worth the complexity.**
Separating scoring weights into `weights.yaml` with a TTL cache allows
threshold changes to propagate within 60 seconds without a deployment.
This makes the feedback loop between experimentation and production
dramatically shorter.

**Dead-letter queues need longer retention than main topics.**
Failed messages require investigation before replay. A 7-day DLQ means
messages expire before the root cause is understood. 30 days is the
minimum for a production incident cycle.

**Deterministic A/B assignment is non-negotiable.**
Hash-based assignment ensures the same event always maps to the same
variant, making experiments reproducible from logs and preventing the
same event from being counted in both arms.

**In-memory analytics engines are fully testable without infrastructure.**
Building `QualityAnalyticsEngine`, `RCAEngine`, and `ExperimentEngine`
as pure in-memory classes with Kafka consumers as thin wrappers means
every method is unit-testable with no database, no Kafka broker, and no
mocking of infrastructure. 

**Lazy imports are essential for scripts that use heavy SDKs as side effects.**
MLflow's import chain pulls in pandas, polars, numpy, scipy, pyarrow, fastapi, and IPython — adding over 3 seconds to any script that imports it at module level. Moving the import inside the function that actually uses it, and running that function in a background thread, keeps script startup instant and progress bars responsive.

**Daemon threads are silently killed when the main process exits.**
Using `daemon=True` on the MLflow logging thread means it gets killed before finishing if the script exits quickly. Setting `daemon=False` and calling `t.join(timeout=30)` ensures the run is fully written to the tracking server before the process exits.

**Docker service networking requires explicit network membership.**
A new container added to an existing compose stack does not automatically join the networks of sibling services. Hostname resolution between containers only works when both are on the same Docker network. Declaring external networks explicitly in the compose file and assigning both services to the same network is the correct fix.

---

## 24. Next Steps

- Make risk thresholds configurable via environment variables in addition to weights.yaml  
- Add API authentication for production-style local deployments and testing  
- Monitoring and observability — add structured logging, latency metrics, queue timing, and per-service performance dashboards  
- Add traceability and audit logging for reviewer actions and policy changes  
- Error recovery — implement checkpointed consumer recovery and safe replay handling for failed processing stages  
- Latency optimisation — parallelise detector execution further and cache repeated enrichment/scoring lookups with a short TTL  
- Add explainable AI outputs showing which rules, heuristics, and detector signals contributed most to each risk score  
- Add source-level evidence and decision explanations directly into RCA and analytics reports  
- Add reviewer performance analytics including disagreement tracking and workload balancing  
- Expand the evaluation framework to separately measure routing quality, escalation quality, reviewer consistency, and business impact  
- Add policy simulation and replay tooling to validate threshold changes against historical traffic  
- Visualise escalation flows, reviewer queues, and RCA clusters in a local Streamlit UI  
- Replace the placeholder classifier with a stronger model trained on larger synthetic or labelled datasets  
- Advanced feature engineering — move from static heuristics to temporal and behavioural feature aggregation  
- Add hallucination/over-escalation reduction by validating detector outputs against historical reviewer outcomes  
- Add active learning pipelines where reviewer outcomes automatically generate retraining datasets  
- Add online drift adaptation with automatic retraining triggers  
- Add multilingual event support for moderation-style payloads before scoring and routing  
- Add PII detection and redaction before persistence into PostgreSQL or DLQs  
- Add chaos-testing simulations for Kafka outages, lag spikes, and service recovery behaviour  
- Add adaptive autoscaling simulations combining Kafka lag, SLA breaches, and queue age  
- Add graph-based anomaly detection using Neo4j locally for linked-event analysis  
- Extend the experimentation framework with contextual bandits instead of static A/B assignment  
- Introduce reinforcement-learning or preference-optimised routing strategies using reviewer outcomes as feedback  
- Add prompt-injection and adversarial-input detection for future LLM-assisted moderation workflows  
- Add MLflow model comparison across training runs with automatic promotion gating on F1 threshold  
- Add MLflow Projects integration so each experiment run is fully reproducible from a single command  
- Connect MLflow model registry to the routing engine so threshold changes trigger automatic remaining experiments  
---


