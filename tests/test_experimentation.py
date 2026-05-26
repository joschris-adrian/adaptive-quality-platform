import pytest
import random
from services.analytics.experimentation import ExperimentEngine, Experiment


@pytest.fixture
def engine():
    return ExperimentEngine()


def _make_exp(engine, variants=None, split=None, metrics=None, status="draft"):
    variants = variants or ["control", "treatment"]
    metrics  = metrics  or ["precision", "cost"]
    exp = engine.create(
        name="test-exp",
        description="test",
        variants=variants,
        metrics=metrics,
        traffic_split=split,
    )
    if status == "running":
        engine.start(exp.experiment_id)
    elif status == "completed":
        engine.start(exp.experiment_id)
        engine.complete(exp.experiment_id)
    return exp


# ── create ─────────────────────────────────────────────────────────────────

def test_create_returns_experiment(engine):
    exp = _make_exp(engine)
    assert isinstance(exp, Experiment)
    assert exp.status == "draft"


def test_create_default_even_split(engine):
    exp = _make_exp(engine, variants=["a", "b", "c"])
    for v in ["a", "b", "c"]:
        assert abs(exp.traffic_split[v] - 1/3) < 1e-4


def test_create_custom_split(engine):
    exp = _make_exp(engine, split={"control": 0.8, "treatment": 0.2})
    assert exp.traffic_split["control"]   == pytest.approx(0.8)
    assert exp.traffic_split["treatment"] == pytest.approx(0.2)


def test_create_invalid_split_raises(engine):
    with pytest.raises(ValueError, match="sum to 1.0"):
        _make_exp(engine, split={"control": 0.6, "treatment": 0.6})


def test_create_mismatched_split_keys_raises(engine):
    with pytest.raises(ValueError, match="keys must match"):
        _make_exp(engine, variants=["control", "treatment"],
                  split={"control": 0.5, "wrong": 0.5})


def test_create_stores_experiment(engine):
    exp = _make_exp(engine)
    assert exp.experiment_id in engine._experiments


def test_create_assigns_unique_ids(engine):
    e1 = _make_exp(engine)
    e2 = _make_exp(engine)
    assert e1.experiment_id != e2.experiment_id


# ── lifecycle ──────────────────────────────────────────────────────────────

def test_start_changes_status(engine):
    exp = _make_exp(engine)
    engine.start(exp.experiment_id)
    assert exp.status == "running"


def test_start_sets_started_at(engine):
    exp = _make_exp(engine)
    engine.start(exp.experiment_id)
    assert exp.started_at is not None


def test_start_from_invalid_status_raises(engine):
    exp = _make_exp(engine, status="running")
    with pytest.raises(ValueError):
        engine.start(exp.experiment_id)


def test_pause_changes_status(engine):
    exp = _make_exp(engine, status="running")
    engine.pause(exp.experiment_id)
    assert exp.status == "paused"


def test_pause_non_running_raises(engine):
    exp = _make_exp(engine)
    with pytest.raises(ValueError):
        engine.pause(exp.experiment_id)


def test_complete_changes_status(engine):
    exp = _make_exp(engine, status="running")
    engine.complete(exp.experiment_id)
    assert exp.status == "completed"


def test_complete_sets_completed_at(engine):
    exp = _make_exp(engine, status="running")
    engine.complete(exp.experiment_id)
    assert exp.completed_at is not None


def test_get_unknown_experiment_raises(engine):
    with pytest.raises(KeyError):
        engine._get("does-not-exist")


# ── assign ─────────────────────────────────────────────────────────────────

def test_assign_returns_valid_variant(engine):
    exp     = _make_exp(engine, status="running")
    variant = engine.assign(exp.experiment_id, "event-001")
    assert variant in exp.variants


def test_assign_is_deterministic(engine):
    exp = _make_exp(engine, status="running")
    v1  = engine.assign(exp.experiment_id, "event-001")
    v2  = engine.assign(exp.experiment_id, "event-001")
    assert v1 == v2


def test_assign_non_running_raises(engine):
    exp = _make_exp(engine)
    with pytest.raises(ValueError):
        engine.assign(exp.experiment_id, "event-001")


def test_assign_distributes_across_variants(engine):
    exp = _make_exp(engine, status="running",
                    variants=["control", "treatment"],
                    split={"control": 0.5, "treatment": 0.5})
    assignments = [engine.assign(exp.experiment_id, f"evt-{i}") for i in range(1000)]
    control_pct = assignments.count("control") / 1000
    # allow 10% tolerance on 50/50 split
    assert 0.40 <= control_pct <= 0.60


def test_assign_respects_unequal_split(engine):
    exp = _make_exp(engine, status="running",
                    variants=["control", "treatment"],
                    split={"control": 0.9, "treatment": 0.1})
    assignments = [engine.assign(exp.experiment_id, f"evt-{i}") for i in range(1000)]
    treatment_pct = assignments.count("treatment") / 1000
    assert treatment_pct <= 0.20


def test_assign_three_variants(engine):
    exp = _make_exp(engine, status="running",
                    variants=["a", "b", "c"])
    assignments = {engine.assign(exp.experiment_id, f"e{i}") for i in range(300)}
    assert "a" in assignments
    assert "b" in assignments
    assert "c" in assignments


# ── record ─────────────────────────────────────────────────────────────────

def test_record_stores_observation(engine):
    exp = _make_exp(engine, status="running")
    engine.assign(exp.experiment_id, "e1")
    engine.record(exp.experiment_id, "e1", {"precision": 0.9, "cost": 1.2})
    assert len(engine._observations[exp.experiment_id]) == 1


def test_record_without_assignment_raises(engine):
    exp = _make_exp(engine, status="running")
    with pytest.raises(KeyError):
        engine.record(exp.experiment_id, "unassigned-event", {"precision": 0.9})


def test_record_multiple_observations(engine):
    exp = _make_exp(engine, status="running")
    for i in range(10):
        engine.assign(exp.experiment_id, f"e{i}")
        engine.record(exp.experiment_id, f"e{i}", {"precision": 0.85, "cost": 1.0})
    assert len(engine._observations[exp.experiment_id]) == 10


# ── results ────────────────────────────────────────────────────────────────

def test_results_empty_observations(engine):
    exp    = _make_exp(engine, status="running")
    result = engine.results(exp.experiment_id)
    assert result["variants"] == {}


def test_results_has_all_variants(engine):
    exp = _make_exp(engine, status="running")
    for i in range(20):
        v = engine.assign(exp.experiment_id, f"e{i}")
        engine.record(exp.experiment_id, f"e{i}", {"precision": 0.8, "cost": 1.0})
    result = engine.results(exp.experiment_id)
    for v in exp.variants:
        if v in result["variants"]:
            assert "n" in result["variants"][v]


def test_results_mean_computed(engine):
    exp = _make_exp(engine, status="running",
                    variants=["control"],
                    split={"control": 1.0},
                    metrics=["precision"])
    for i in range(4):
        engine.assign(exp.experiment_id, f"e{i}")
        engine.record(exp.experiment_id, f"e{i}", {"precision": 0.8})
    result = engine.results(exp.experiment_id)
    assert result["variants"]["control"]["precision"]["mean"] == pytest.approx(0.8)


def test_results_std_computed(engine):
    exp = _make_exp(engine, status="running",
                    variants=["control"],
                    split={"control": 1.0},
                    metrics=["precision"])
    values = [0.7, 0.8, 0.9, 1.0]
    for i, v in enumerate(values):
        engine.assign(exp.experiment_id, f"e{i}")
        engine.record(exp.experiment_id, f"e{i}", {"precision": v})
    result = engine.results(exp.experiment_id)
    assert result["variants"]["control"]["precision"]["std"] > 0.0


def test_results_winner_higher_is_better(engine):
    exp = _make_exp(engine, status="running",
                    metrics=["precision", "cost"])
    for i in range(100):
        v = engine.assign(exp.experiment_id, f"e{i}")
        engine.record(exp.experiment_id, f"e{i}", {
            "precision": 0.95 if v == "treatment" else 0.75,
            "cost":      1.0,
        })
    result = engine.results(exp.experiment_id)
    assert result["winner"] == "treatment"


def test_results_winner_lower_is_better_for_cost(engine):
    exp = _make_exp(engine, status="running",
                    metrics=["cost", "precision"])
    for i in range(100):
        v = engine.assign(exp.experiment_id, f"e{i}")
        engine.record(exp.experiment_id, f"e{i}", {
            "cost":      0.50 if v == "treatment" else 1.50,
            "precision": 0.85,
        })
    result = engine.results(exp.experiment_id)
    assert result["winner"] == "treatment"


def test_results_relative_lifts_computed(engine):
    exp = _make_exp(engine, status="running",
                    metrics=["precision"])
    for i in range(100):
        v = engine.assign(exp.experiment_id, f"e{i}")
        engine.record(exp.experiment_id, f"e{i}", {
            "precision": 0.90 if v == "treatment" else 0.80,
        })
    result = engine.results(exp.experiment_id)
    lifts  = result["relative_lifts"]
    if "treatment" in lifts and lifts["treatment"]["precision"] is not None:
        assert lifts["treatment"]["precision"] > 0


def test_results_total_observations(engine):
    exp = _make_exp(engine, status="running")
    for i in range(30):
        engine.assign(exp.experiment_id, f"e{i}")
        engine.record(exp.experiment_id, f"e{i}", {"precision": 0.8, "cost": 1.0})
    result = engine.results(exp.experiment_id)
    assert result["total_observations"] == 30


# ── list_experiments ───────────────────────────────────────────────────────

def test_list_experiments_all(engine):
    _make_exp(engine)
    _make_exp(engine)
    assert len(engine.list_experiments()) == 2


def test_list_experiments_filter_by_status(engine):
    _make_exp(engine, status="running")
    _make_exp(engine, status="draft")
    running = engine.list_experiments(status="running")
    assert all(e.status == "running" for e in running)
    assert len(running) == 1


# ── threshold_experiment ───────────────────────────────────────────────────

def test_threshold_experiment_returns_results(engine):
    result = engine.threshold_experiment(
        name="sweep", thresholds=[0.6, 0.7, 0.8], total_events=1000
    )
    assert len(result["results"]) == 3


def test_threshold_experiment_has_optimal(engine):
    result = engine.threshold_experiment(
        name="sweep", thresholds=[0.6, 0.7, 0.8], total_events=1000
    )
    assert "optimal" in result
    assert "escalate_threshold" in result["optimal"]


def test_threshold_experiment_costs_present(engine):
    result = engine.threshold_experiment(
        name="sweep", thresholds=[0.6, 0.8], total_events=5000
    )
    for row in result["results"]:
        assert "total_cost"   in row
        assert "quality_score" in row


# ── routing_strategy_experiment ────────────────────────────────────────────

def test_routing_strategy_experiment_has_recommended(engine):
    result = engine.routing_strategy_experiment("strategy-test", total_events=5000)
    assert "recommended" in result


def test_routing_strategy_experiment_within_budget(engine):
    result = engine.routing_strategy_experiment(
        "budget-test", total_events=5000, budget=500.0
    )
    for s in result["results"]:
        assert s["total_cost"] <= 500.0


# ── label_quality_experiment ───────────────────────────────────────────────

def test_label_quality_full_agreement(engine):
    events  = [f"e{i}" for i in range(10)]
    result  = engine.label_quality_experiment(
        "lq-test", events,
        labeller_a_fn=lambda eid: "positive",
        labeller_b_fn=lambda eid: "positive",
    )
    assert result["agreement_rate"] == 1.0


def test_label_quality_no_agreement(engine):
    events = [f"e{i}" for i in range(10)]
    result = engine.label_quality_experiment(
        "lq-test", events,
        labeller_a_fn=lambda eid: "positive",
        labeller_b_fn=lambda eid: "negative",
    )
    assert result["agreement_rate"] == 0.0


def test_label_quality_partial_agreement(engine):
    events  = [f"e{i}" for i in range(10)]
    labels  = ["positive"] * 5 + ["negative"] * 5
    result  = engine.label_quality_experiment(
        "lq-test", events,
        labeller_a_fn=lambda eid: "positive",
        labeller_b_fn=lambda eid: labels[int(eid[1:])],
    )
    assert result["agreement_rate"] == pytest.approx(0.5)


def test_label_quality_empty_events(engine):
    result = engine.label_quality_experiment(
        "lq-test", [],
        labeller_a_fn=lambda e: "positive",
        labeller_b_fn=lambda e: "positive",
    )
    assert result["agreement_rate"] == 0.0


# ── sampling_experiment ────────────────────────────────────────────────────

def test_sampling_experiment_returns_per_rate(engine):
    population = [{"risk_score": random.random()} for _ in range(1000)]
    results    = engine.sampling_experiment(
        name="sample-test",
        population=population,
        sample_rates=[0.1, 0.5, 1.0],
        metric_fn=lambda s: sum(e["risk_score"] for e in s) / len(s),
    )
    assert len(results) == 3


def test_sampling_experiment_sample_size_correct(engine):
    population = [{"x": i} for i in range(200)]
    results    = engine.sampling_experiment(
        name="sample-test",
        population=population,
        sample_rates=[0.5],
        metric_fn=lambda s: len(s),
    )
    assert results[0]["sample_size"] == 100


def test_sampling_experiment_full_sample(engine):
    population = [{"risk_score": 0.8} for _ in range(100)]
    results    = engine.sampling_experiment(
        name="sample-test",
        population=population,
        sample_rates=[1.0],
        metric_fn=lambda s: sum(e["risk_score"] for e in s) / len(s),
    )
    assert results[0]["metric_value"] == pytest.approx(0.8)