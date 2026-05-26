import pytest
from services.analytics.cost       import CostModel, TIER_COSTS
from services.analytics.quality    import QualityMetrics, QualityTracker
from services.analytics.comparison import QualityCostComparator, STRATEGIES


# ── CostModel ──────────────────────────────────────────────────────────────

@pytest.fixture
def cost_model():
    return CostModel()


def test_cost_for_automated_tier(cost_model):
    assert cost_model.cost_for_event("automated") == TIER_COSTS["automated"].cost_per_event


def test_cost_for_expert_tier(cost_model):
    assert cost_model.cost_for_event("expert") == TIER_COSTS["expert"].cost_per_event


def test_batch_cost_totals_correctly(cost_model):
    counts = {"automated": 800, "standard": 150, "expert": 50}
    result = cost_model.compute_batch_cost(counts)

    expected_cost = (
        800 * TIER_COSTS["automated"].cost_per_event +
        150 * TIER_COSTS["standard"].cost_per_event  +
        50  * TIER_COSTS["expert"].cost_per_event
    )
    assert abs(result["total_cost"] - expected_cost) < 0.01


def test_batch_cost_total_events(cost_model):
    counts = {"automated": 800, "standard": 150, "expert": 50}
    result = cost_model.compute_batch_cost(counts)
    assert result["total_events"] == 1000


def test_batch_cost_system_accuracy_weighted(cost_model):
    # All automated → accuracy should equal automated tier accuracy
    counts = {"automated": 1000, "standard": 0, "expert": 0}
    result = cost_model.compute_batch_cost(counts)
    assert abs(result["system_accuracy"] - TIER_COSTS["automated"].accuracy) < 1e-4


def test_batch_cost_breakdown_has_all_tiers(cost_model):
    counts = {"automated": 500, "standard": 300, "expert": 200}
    result = cost_model.compute_batch_cost(counts)
    assert set(result["breakdown"].keys()) == {"automated", "standard", "expert"}


def test_batch_cost_pct_of_volume(cost_model):
    counts = {"automated": 500, "standard": 300, "expert": 200}
    result = cost_model.compute_batch_cost(counts)
    assert result["breakdown"]["automated"]["pct_of_volume"] == pytest.approx(50.0)
    assert result["breakdown"]["standard"]["pct_of_volume"]  == pytest.approx(30.0)
    assert result["breakdown"]["expert"]["pct_of_volume"]    == pytest.approx(20.0)


def test_cost_per_correct_decision_positive(cost_model):
    counts = {"automated": 800, "standard": 150, "expert": 50}
    result = cost_model.compute_batch_cost(counts)
    assert result["cost_per_correct_decision"] > 0


def test_empty_batch_does_not_crash(cost_model):
    counts = {"automated": 0, "standard": 0, "expert": 0}
    result = cost_model.compute_batch_cost(counts)
    assert result["total_cost"]      == 0.0
    assert result["system_accuracy"] == 0.0


# ── QualityMetrics ─────────────────────────────────────────────────────────

def test_precision_all_correct():
    m = QualityMetrics(true_positives=100, false_positives=0)
    assert m.precision == 1.0


def test_precision_half_correct():
    m = QualityMetrics(true_positives=50, false_positives=50)
    assert m.precision == pytest.approx(0.5)


def test_recall_all_caught():
    m = QualityMetrics(true_positives=100, false_negatives=0)
    assert m.recall == 1.0


def test_recall_half_caught():
    m = QualityMetrics(true_positives=50, false_negatives=50)
    assert m.recall == pytest.approx(0.5)


def test_f1_balanced():
    m = QualityMetrics(true_positives=80, false_positives=20, false_negatives=20)
    assert m.f1 == pytest.approx(2 * m.precision * m.recall / (m.precision + m.recall))


def test_f1_zero_when_no_positives():
    m = QualityMetrics()
    assert m.f1 == 0.0


def test_false_positive_rate():
    m = QualityMetrics(false_positives=10, true_negatives=90)
    assert m.false_positive_rate == pytest.approx(0.1)


def test_false_negative_rate():
    m = QualityMetrics(true_positives=90, false_negatives=10)
    assert m.false_negative_rate == pytest.approx(0.1)


def test_accuracy_all_correct():
    m = QualityMetrics(true_positives=50, true_negatives=50)
    assert m.accuracy == 1.0


def test_accuracy_zero_when_empty():
    m = QualityMetrics()
    assert m.accuracy == 0.0


def test_to_dict_has_all_keys():
    m    = QualityMetrics(true_positives=10, false_positives=2, true_negatives=8, false_negatives=1)
    d    = m.to_dict()
    keys = ["precision", "recall", "f1", "accuracy",
            "false_positive_rate", "false_negative_rate",
            "true_positives", "false_positives", "true_negatives", "false_negatives"]
    for k in keys:
        assert k in d


# ── QualityTracker ─────────────────────────────────────────────────────────

@pytest.fixture
def tracker():
    return QualityTracker()


def test_tracker_records_true_positive(tracker):
    tracker.record("standard", "fraud", "positive", "positive")
    assert tracker._global.true_positives == 1


def test_tracker_records_false_positive(tracker):
    tracker.record("automated", "spam", "positive", "negative")
    assert tracker._global.false_positives == 1


def test_tracker_records_true_negative(tracker):
    tracker.record("automated", "clean", "negative", "negative")
    assert tracker._global.true_negatives == 1


def test_tracker_records_false_negative(tracker):
    tracker.record("expert", "fraud", "negative", "positive")
    assert tracker._global.false_negatives == 1


def test_tracker_segments_by_tier(tracker):
    tracker.record("standard", "fraud", "positive", "positive")
    tracker.record("expert",   "fraud", "positive", "positive")
    assert tracker._by_tier["standard"].true_positives == 1
    assert tracker._by_tier["expert"].true_positives   == 1


def test_tracker_segments_by_category(tracker):
    tracker.record("standard", "fraud", "positive", "positive")
    tracker.record("standard", "spam",  "positive", "positive")
    assert tracker._by_category["fraud"].true_positives == 1
    assert tracker._by_category["spam"].true_positives  == 1


def test_tracker_report_structure(tracker):
    tracker.record("standard", "fraud", "positive", "positive")
    report = tracker.report()
    assert "global"      in report
    assert "by_tier"     in report
    assert "by_category" in report


def test_tracker_global_accumulates_all(tracker):
    tracker.record("standard",  "fraud", "positive", "positive")
    tracker.record("automated", "spam",  "negative", "negative")
    tracker.record("expert",    "abuse", "positive", "negative")
    assert tracker._global.true_positives  == 1
    assert tracker._global.true_negatives  == 1
    assert tracker._global.false_positives == 1


# ── QualityCostComparator ──────────────────────────────────────────────────

@pytest.fixture
def comparator():
    return QualityCostComparator()


def test_compare_strategies_returns_all(comparator):
    result = comparator.compare_strategies(10_000)
    for name in STRATEGIES:
        assert name in result["strategies"]


def test_compare_strategies_has_recommendation(comparator):
    result = comparator.compare_strategies(10_000)
    assert result["recommended"] in STRATEGIES


def test_automation_only_is_cheapest(comparator):
    result     = comparator.compare_strategies(10_000)
    strategies = result["strategies"]
    costs      = {n: d["total_cost"] for n, d in strategies.items()}
    assert costs["automation_only"] == min(costs.values())


def test_human_heavy_is_most_accurate(comparator):
    result     = comparator.compare_strategies(10_000)
    strategies = result["strategies"]
    accuracies = {n: d["system_accuracy"] for n, d in strategies.items()}
    assert accuracies["human_heavy"] == max(accuracies.values())


def test_quality_score_bounded(comparator):
    result = comparator.compare_strategies(10_000)
    for data in result["strategies"].values():
        assert 0.0 <= data["quality_score"] <= 1.0


def test_efficiency_ratio_positive(comparator):
    result = comparator.compare_strategies(10_000)
    for data in result["strategies"].values():
        assert data["efficiency_ratio"] >= 0.0


def test_threshold_sensitivity_returns_list(comparator):
    rows = comparator.threshold_sensitivity(10_000)
    assert isinstance(rows, list)
    assert len(rows) > 0


def test_threshold_sensitivity_cost_increases_with_lower_threshold(comparator):
    rows  = comparator.threshold_sensitivity(10_000)
    costs = [r["total_cost"] for r in rows]
    # Lower threshold → more escalation → higher cost
    # List is ordered from low to high threshold, so costs should decrease
    assert costs[0] >= costs[-1]


def test_budget_report_filters_correctly(comparator):
    # Very low budget — only automation_only should fit
    affordable = comparator.cost_under_budget(10_000, budget=50.0)
    for s in affordable:
        assert s["total_cost"] <= 50.0


def test_budget_report_sorted_by_quality(comparator):
    affordable = comparator.cost_under_budget(10_000, budget=50_000.0)
    qualities  = [s["quality_score"] for s in affordable]
    assert qualities == sorted(qualities, reverse=True)


def test_budget_report_empty_when_budget_zero(comparator):
    affordable = comparator.cost_under_budget(10_000, budget=0.0)
    assert affordable == []