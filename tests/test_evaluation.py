import pytest
from services.analytics.evaluation import (
    QualityMetricsCalculator,
    OperationalMetricsCalculator,
    BusinessMetricsCalculator,
    EvaluationSuite,
    EvaluationResult,
)


# ── fixtures ───────────────────────────────────────────────────────────────

@pytest.fixture
def quality():
    return QualityMetricsCalculator()


@pytest.fixture
def operational():
    return OperationalMetricsCalculator()


@pytest.fixture
def business():
    return BusinessMetricsCalculator()


@pytest.fixture
def suite():
    return EvaluationSuite()


def _result(
    tp=80, fp=10, tn=90, fn=20,
    latencies=None, elapsed=1.0,
    cpu=50.0, memory=40.0,
    cost=500.0, reviewed=100,
    high_risk_esc=70, total_high_risk=80,
    total_esc=90,
):
    suite = EvaluationSuite()
    return suite.evaluate(
        tp=tp, fp=fp, tn=tn, fn=fn,
        latencies_ms=        latencies or [100.0] * 50 + [500.0] * 10,
        elapsed_seconds=     elapsed,
        cpu_pct=             cpu,
        memory_pct=          memory,
        total_cost=          cost,
        reviewed_events=     reviewed,
        high_risk_escalated= high_risk_esc,
        total_high_risk=     total_high_risk,
        total_escalated=     total_esc,
    )


# ── QualityMetricsCalculator ───────────────────────────────────────────────

class TestQualityMetrics:

    def test_precision_all_correct(self, quality):
        r = quality.compute(tp=100, fp=0, tn=50, fn=0)
        assert r["precision"] == 1.0

    def test_precision_half_correct(self, quality):
        r = quality.compute(tp=50, fp=50, tn=0, fn=0)
        assert r["precision"] == pytest.approx(0.5)

    def test_recall_all_caught(self, quality):
        r = quality.compute(tp=100, fp=0, tn=50, fn=0)
        assert r["recall"] == 1.0

    def test_recall_half_caught(self, quality):
        r = quality.compute(tp=50, fp=0, tn=0, fn=50)
        assert r["recall"] == pytest.approx(0.5)

    def test_f1_balanced(self, quality):
        r = quality.compute(tp=80, fp=20, tn=80, fn=20)
        p, rec = r["precision"], r["recall"]
        assert r["f1"] == pytest.approx(2 * p * rec / (p + rec), abs=1e-4)

    def test_f1_zero_when_no_positives(self, quality):
        r = quality.compute(tp=0, fp=0, tn=100, fn=0)
        assert r["f1"] == 0.0

    def test_false_positive_rate(self, quality):
        r = quality.compute(tp=0, fp=10, tn=90, fn=0)
        assert r["false_positive_rate"] == pytest.approx(0.1)

    def test_false_negative_rate(self, quality):
        r = quality.compute(tp=90, fp=0, tn=0, fn=10)
        assert r["false_negative_rate"] == pytest.approx(0.1)

    def test_accuracy_all_correct(self, quality):
        r = quality.compute(tp=50, fp=0, tn=50, fn=0)
        assert r["accuracy"] == 1.0

    def test_accuracy_formula(self, quality):
        r = quality.compute(tp=70, fp=10, tn=80, fn=20)
        assert r["accuracy"] == pytest.approx((70 + 80) / 180, abs=1e-4)

    def test_all_zeros_returns_zeros(self, quality):
        r = quality.compute(tp=0, fp=0, tn=0, fn=0)
        assert r["precision"] == 0.0
        assert r["recall"]    == 0.0
        assert r["f1"]        == 0.0

    def test_error_rate(self, quality):
        rate = quality.error_rate(tp=80, fp=10, tn=90, fn=20)
        assert rate == pytest.approx(30 / 200, abs=1e-4)

    def test_error_rate_zero_total(self, quality):
        assert quality.error_rate(0, 0, 0, 0) == 0.0

    def test_compute_by_category_splits_correctly(self, quality):
        records = [
            {"category": "fraud", "predicted": "positive", "ground_truth": "positive"},
            {"category": "fraud", "predicted": "positive", "ground_truth": "negative"},
            {"category": "spam",  "predicted": "negative", "ground_truth": "negative"},
        ]
        result = quality.compute_by_category(records)
        assert result["fraud"]["tp"] == 1
        assert result["fraud"]["fp"] == 1
        assert result["spam"]["tn"]  == 1

    def test_compute_by_category_precision(self, quality):
        records = [
            {"category": "fraud", "predicted": "positive", "ground_truth": "positive"},
            {"category": "fraud", "predicted": "positive", "ground_truth": "positive"},
        ]
        result = quality.compute_by_category(records)
        assert result["fraud"]["precision"] == 1.0

    def test_macro_average_equal_categories(self, quality):
        per_cat = {
            "fraud": quality.compute(tp=80, fp=20, tn=80, fn=20),
            "spam":  quality.compute(tp=40, fp=10, tn=40, fn=10),
        }
        macro = quality.macro_average(per_cat)
        assert macro["precision"] == pytest.approx(
            (per_cat["fraud"]["precision"] + per_cat["spam"]["precision"]) / 2,
            abs=1e-4,
        )

    def test_macro_average_empty(self, quality):
        result = quality.macro_average({})
        assert result["precision"] == 0.0

    def test_weighted_average_single_category(self, quality):
        per_cat = {"fraud": quality.compute(tp=80, fp=20, tn=60, fn=10)}
        weighted = quality.weighted_average(per_cat)
        assert weighted["precision"] == per_cat["fraud"]["precision"]

    def test_weighted_average_empty(self, quality):
        result = quality.weighted_average({})
        assert result["precision"] == 0.0


# ── OperationalMetricsCalculator ───────────────────────────────────────────

class TestOperationalMetrics:

    def test_queue_latency_empty(self, operational):
        result = operational.queue_latency([])
        assert result["avg_ms"] == 0.0
        assert result["p95_ms"] == 0.0

    def test_queue_latency_avg(self, operational):
        result = operational.queue_latency([100.0, 200.0, 300.0])
        assert result["avg_ms"] == pytest.approx(200.0)

    def test_queue_latency_p95(self, operational):
        latencies = list(range(1, 101))   # 1..100
        result    = operational.queue_latency([float(x) for x in latencies])
        assert result["p95_ms"] >= 95.0

    def test_queue_latency_min_max(self, operational):
        result = operational.queue_latency([50.0, 100.0, 200.0])
        assert result["min_ms"] == 50.0
        assert result["max_ms"] == 200.0

    def test_queue_latency_single_value(self, operational):
        result = operational.queue_latency([150.0])
        assert result["avg_ms"] == 150.0
        assert result["min_ms"] == 150.0
        assert result["max_ms"] == 150.0

    def test_throughput_basic(self, operational):
        assert operational.throughput(1000, 10.0) == pytest.approx(100.0)

    def test_throughput_zero_elapsed(self, operational):
        assert operational.throughput(1000, 0.0) == 0.0

    def test_throughput_zero_events(self, operational):
        assert operational.throughput(0, 10.0) == 0.0

    def test_resource_utilisation_basic(self, operational):
        result = operational.resource_utilisation(cpu_pct=60.0, memory_pct=40.0)
        expected = (60.0 * 0.6 + 40.0 * 0.4) / 100
        assert result == pytest.approx(expected, abs=1e-4)

    def test_resource_utilisation_capped_at_one(self, operational):
        result = operational.resource_utilisation(cpu_pct=100.0, memory_pct=100.0)
        assert result == 1.0

    def test_resource_utilisation_zero(self, operational):
        assert operational.resource_utilisation(0.0, 0.0) == 0.0

    def test_queue_backlog_healthy(self, operational):
        result = operational.queue_backlog_health(
            pending=50, capacity_limit=500,
            oldest_pending_ms=1000, sla_ms=60_000,
        )
        assert result["status"] == "healthy"

    def test_queue_backlog_warning(self, operational):
        result = operational.queue_backlog_health(
            pending=370, capacity_limit=500,
            oldest_pending_ms=1000, sla_ms=60_000,
        )
        assert result["status"] == "warning"

    def test_queue_backlog_critical_by_fill(self, operational):
        result = operational.queue_backlog_health(
            pending=460, capacity_limit=500,
            oldest_pending_ms=1000, sla_ms=60_000,
        )
        assert result["status"] == "critical"

    def test_queue_backlog_critical_by_sla(self, operational):
        result = operational.queue_backlog_health(
            pending=10, capacity_limit=500,
            oldest_pending_ms=90_000, sla_ms=60_000,
        )
        assert result["status"]    == "critical"
        assert result["sla_breach"] is True

    def test_queue_backlog_sla_no_breach(self, operational):
        result = operational.queue_backlog_health(
            pending=10, capacity_limit=500,
            oldest_pending_ms=1000, sla_ms=60_000,
        )
        assert result["sla_breach"] is False

    def test_queue_backlog_queue_pct(self, operational):
        result = operational.queue_backlog_health(
            pending=250, capacity_limit=500,
            oldest_pending_ms=0, sla_ms=60_000,
        )
        assert result["queue_pct"] == pytest.approx(0.5)


# ── BusinessMetricsCalculator ──────────────────────────────────────────────

class TestBusinessMetrics:

    def test_cost_per_reviewed_event(self, business):
        assert business.cost_per_reviewed_event(500.0, 100) == pytest.approx(5.0)

    def test_cost_per_reviewed_event_zero_reviewed(self, business):
        assert business.cost_per_reviewed_event(500.0, 0) == 0.0

    def test_cost_per_reviewed_event_zero_cost(self, business):
        assert business.cost_per_reviewed_event(0.0, 100) == 0.0

    def test_high_risk_capture_rate_perfect(self, business):
        assert business.high_risk_capture_rate(100, 100) == 1.0

    def test_high_risk_capture_rate_partial(self, business):
        assert business.high_risk_capture_rate(70, 100) == pytest.approx(0.7)

    def test_high_risk_capture_rate_zero_total(self, business):
        assert business.high_risk_capture_rate(0, 0) == 0.0

    def test_escalation_efficiency_perfect(self, business):
        assert business.escalation_efficiency(100, 100) == 1.0

    def test_escalation_efficiency_partial(self, business):
        assert business.escalation_efficiency(60, 100) == pytest.approx(0.6)

    def test_escalation_efficiency_zero_escalated(self, business):
        assert business.escalation_efficiency(0, 0) == 0.0

    def test_cost_per_correct_decision(self, business):
        assert business.cost_per_correct_decision(900.0, 300) == pytest.approx(3.0)

    def test_cost_per_correct_decision_zero(self, business):
        assert business.cost_per_correct_decision(900.0, 0) == 0.0

    def test_roi_positive(self, business):
        roi = business.roi(value_of_caught_events=1000.0, total_cost=200.0)
        assert roi == pytest.approx(4.0)

    def test_roi_negative(self, business):
        roi = business.roi(value_of_caught_events=100.0, total_cost=200.0)
        assert roi == pytest.approx(-0.5)

    def test_roi_zero_cost(self, business):
        assert business.roi(1000.0, 0.0) == 0.0

    def test_false_negative_business_cost(self, business):
        cost = business.false_negative_business_cost(fn_count=10, cost_per_miss=500.0)
        assert cost == pytest.approx(5000.0)

    def test_false_negative_business_cost_zero(self, business):
        assert business.false_negative_business_cost(0, 500.0) == 0.0


# ── EvaluationSuite ────────────────────────────────────────────────────────

class TestEvaluationSuite:

    def test_evaluate_returns_result(self, suite):
        result = _result()
        assert isinstance(result, EvaluationResult)

    def test_evaluate_to_dict_structure(self, suite):
        d = _result().to_dict()
        assert "quality"     in d
        assert "operational" in d
        assert "business"    in d
        assert "counts"      in d

    def test_evaluate_quality_keys(self, suite):
        d = _result().to_dict()
        for k in ["precision", "recall", "f1",
                  "false_positive_rate", "false_negative_rate", "accuracy"]:
            assert k in d["quality"]

    def test_evaluate_operational_keys(self, suite):
        d = _result().to_dict()
        for k in ["avg_queue_latency_ms", "p95_queue_latency_ms",
                  "throughput_per_second", "resource_utilisation"]:
            assert k in d["operational"]

    def test_evaluate_business_keys(self, suite):
        d = _result().to_dict()
        for k in ["cost_per_reviewed_event",
                  "high_risk_capture_rate", "escalation_efficiency"]:
            assert k in d["business"]

    def test_evaluate_precision_correct(self, suite):
        result = _result(tp=80, fp=20)
        assert result.precision == pytest.approx(80 / 100, abs=1e-4)

    def test_evaluate_recall_correct(self, suite):
        result = _result(tp=80, fn=20)
        assert result.recall == pytest.approx(80 / 100, abs=1e-4)

    def test_evaluate_throughput_correct(self, suite):
        result = _result(tp=50, fp=10, tn=30, fn=10, elapsed=1.0)
        assert result.throughput_per_second == pytest.approx(100.0)

    def test_evaluate_resource_utilisation_bounded(self, suite):
        result = _result(cpu=80.0, memory=60.0)
        assert 0.0 <= result.resource_utilisation <= 1.0

    def test_evaluate_high_risk_capture_rate(self, suite):
        result = _result(high_risk_esc=70, total_high_risk=100)
        assert result.high_risk_capture_rate == pytest.approx(0.70)

    def test_evaluate_cost_per_reviewed_event(self, suite):
        result = _result(cost=500.0, reviewed=100)
        assert result.cost_per_reviewed_event == pytest.approx(5.0)

    def test_evaluate_total_decisions(self, suite):
        result = _result(tp=80, fp=10, tn=90, fn=20)
        assert result.total_decisions == 200

    def test_evaluate_support_keys(self, suite):
        result = _result()
        assert "tp" in result.support
        assert "fp" in result.support
        assert "tn" in result.support
        assert "fn" in result.support

    # ── compare ────────────────────────────────────────────────────────────

    def test_compare_returns_lifts(self, suite):
        baseline  = _result(tp=70, fp=20, tn=80, fn=30)
        treatment = _result(tp=85, fp=10, tn=85, fn=20)
        result    = suite.compare(baseline, treatment)
        assert "quality_lifts"      in result
        assert "operational_lifts"  in result
        assert "business_lifts"     in result
        assert "winner"             in result

    def test_compare_winner_is_valid(self, suite):
        baseline  = _result(tp=70, fp=20, tn=80, fn=30)
        treatment = _result(tp=85, fp=10, tn=85, fn=20)
        result    = suite.compare(baseline, treatment)
        assert result["winner"] in ("baseline", "treatment")

    def test_compare_better_treatment_wins(self, suite):
        baseline  = _result(tp=50, fp=40, tn=60, fn=50, cost=1000.0)
        treatment = _result(tp=90, fp=10, tn=80, fn=10, cost=500.0)
        result    = suite.compare(baseline, treatment)
        assert result["winner"] == "treatment"

    def test_compare_worse_treatment_loses(self, suite):
        baseline  = _result(tp=90, fp=10, tn=80, fn=10, cost=500.0)
        treatment = _result(tp=50, fp=40, tn=60, fn=50, cost=1000.0)
        result    = suite.compare(baseline, treatment)
        assert result["winner"] == "baseline"

    def test_compare_precision_lift_positive_when_treatment_better(self, suite):
        baseline  = _result(tp=60, fp=40, tn=60, fn=40)
        treatment = _result(tp=90, fp=10, tn=90, fn=10)
        result    = suite.compare(baseline, treatment)
        assert result["quality_lifts"]["precision"] > 0

    def test_compare_identical_results(self, suite):
        baseline  = _result()
        treatment = _result()
        result    = suite.compare(baseline, treatment)
        assert result["quality_lifts"]["precision"] == pytest.approx(0.0)

    def test_compare_lift_zero_baseline_returns_none(self, suite):
        baseline  = _result(tp=0, fp=0, tn=100, fn=0)
        treatment = _result(tp=80, fp=10, tn=80, fn=10)
        result    = suite.compare(baseline, treatment)
        assert result["quality_lifts"]["precision"] is None