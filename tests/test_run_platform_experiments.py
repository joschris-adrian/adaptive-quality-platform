import pytest
from scripts.run_platform_experiments import (
    run_strategy_comparison,
    run_threshold_sweep,
    run_budget_experiment,
    run_all,
    TOTAL_EVENTS,
    BUDGET,
)


# ── run_strategy_comparison ────────────────────────────────────────────────

@pytest.fixture
def strategy_result():
    return run_strategy_comparison(TOTAL_EVENTS)


def test_strategy_comparison_returns_dict(strategy_result):
    assert isinstance(strategy_result, dict)


def test_strategy_comparison_has_strategies(strategy_result):
    assert "strategies" in strategy_result


def test_strategy_comparison_has_recommended(strategy_result):
    assert "recommended"        in strategy_result
    assert strategy_result["recommended"] in strategy_result["strategies"]


def test_strategy_comparison_has_all_four_strategies(strategy_result):
    for name in ["automation_only", "hybrid_balanced",
                 "hybrid_quality_first", "human_heavy"]:
        assert name in strategy_result["strategies"]


def test_strategy_comparison_automation_cheapest(strategy_result):
    costs = {
        name: data["total_cost"]
        for name, data in strategy_result["strategies"].items()
    }
    assert costs["automation_only"] == min(costs.values())


def test_strategy_comparison_human_heavy_highest_quality(strategy_result):
    qualities = {
        name: data["quality_score"]
        for name, data in strategy_result["strategies"].items()
    }
    assert qualities["human_heavy"] == max(qualities.values())


def test_strategy_comparison_each_strategy_has_cost(strategy_result):
    for data in strategy_result["strategies"].values():
        assert "total_cost"    in data
        assert data["total_cost"] >= 0


def test_strategy_comparison_each_strategy_has_quality(strategy_result):
    for data in strategy_result["strategies"].values():
        assert "quality_score" in data
        assert 0.0 <= data["quality_score"] <= 1.0


def test_strategy_comparison_each_strategy_has_efficiency(strategy_result):
    for data in strategy_result["strategies"].values():
        assert "efficiency_ratio" in data
        assert data["efficiency_ratio"] >= 0.0


def test_strategy_comparison_total_events(strategy_result):
    assert strategy_result["total_events"] == TOTAL_EVENTS


# ── run_threshold_sweep ────────────────────────────────────────────────────

@pytest.fixture
def threshold_result():
    return run_threshold_sweep(
        total_events=TOTAL_EVENTS,
        thresholds=[0.60, 0.70, 0.80],
    )


def test_threshold_sweep_returns_dict(threshold_result):
    assert isinstance(threshold_result, dict)


def test_threshold_sweep_has_results(threshold_result):
    assert "results" in threshold_result


def test_threshold_sweep_result_count(threshold_result):
    assert len(threshold_result["results"]) == 3


def test_threshold_sweep_has_optimal(threshold_result):
    assert "optimal" in threshold_result
    assert "escalate_threshold" in threshold_result["optimal"]


def test_threshold_sweep_optimal_in_results(threshold_result):
    thresholds = [r["escalate_threshold"] for r in threshold_result["results"]]
    assert threshold_result["optimal"]["escalate_threshold"] in thresholds


def test_threshold_sweep_each_row_has_cost(threshold_result):
    for row in threshold_result["results"]:
        assert "total_cost"   in row
        assert row["total_cost"] >= 0


def test_threshold_sweep_each_row_has_quality(threshold_result):
    for row in threshold_result["results"]:
        assert "quality_score" in row
        assert 0.0 <= row["quality_score"] <= 1.0


def test_threshold_sweep_each_row_has_tier_split(threshold_result):
    for row in threshold_result["results"]:
        assert "tier_split" in row
        sp = row["tier_split"]
        assert "automated" in sp
        assert "standard"  in sp
        assert "expert"    in sp


def test_threshold_sweep_costs_vary(threshold_result):
    costs = [r["total_cost"] for r in threshold_result["results"]]
    assert len(set(costs)) > 1


def test_threshold_sweep_higher_threshold_lower_cost():
    result = run_threshold_sweep(
        total_events=1000,
        thresholds=[0.50, 0.90],
    )
    rows   = result["results"]
    cost_low_threshold  = rows[0]["total_cost"]
    cost_high_threshold = rows[1]["total_cost"]
    assert cost_high_threshold <= cost_low_threshold


# ── run_budget_experiment ──────────────────────────────────────────────────

@pytest.fixture
def budget_result():
    return run_budget_experiment(TOTAL_EVENTS, BUDGET)


def test_budget_experiment_returns_list(budget_result):
    assert isinstance(budget_result, list)


def test_budget_experiment_all_within_budget(budget_result):
    for s in budget_result:
        assert s["total_cost"] <= BUDGET


def test_budget_experiment_sorted_by_quality(budget_result):
    if len(budget_result) > 1:
        qualities = [s["quality_score"] for s in budget_result]
        assert qualities == sorted(qualities, reverse=True)


def test_budget_experiment_zero_budget_returns_empty():
    result = run_budget_experiment(TOTAL_EVENTS, budget=0.0)
    assert result == []


def test_budget_experiment_large_budget_returns_all():
    result = run_budget_experiment(TOTAL_EVENTS, budget=999_999.0)
    assert len(result) == 4


def test_budget_experiment_each_has_name(budget_result):
    for s in budget_result:
        assert "name" in s


def test_budget_experiment_each_has_quality(budget_result):
    for s in budget_result:
        assert "quality_score" in s
        assert 0.0 <= s["quality_score"] <= 1.0


# ── run_all ────────────────────────────────────────────────────────────────

@pytest.fixture
def all_results():
    return run_all(total_events=1_000, budget=500.0)


def test_run_all_returns_dict(all_results):
    assert isinstance(all_results, dict)


def test_run_all_has_all_sections(all_results):
    assert "strategy_comparison" in all_results
    assert "threshold_sweep"     in all_results
    assert "budget_experiment"   in all_results
    assert "summary"             in all_results


def test_run_all_summary_has_quality_gain(all_results):
    assert "quality_gain_hybrid_vs_auto" in all_results["summary"]


def test_run_all_summary_has_cost_increase(all_results):
    assert "cost_increase_hybrid_vs_auto" in all_results["summary"]


def test_run_all_summary_has_optimal_threshold(all_results):
    assert "optimal_threshold" in all_results["summary"]


def test_run_all_summary_has_best_affordable(all_results):
    assert "best_affordable_strategy" in all_results["summary"]


def test_run_all_quality_gain_non_negative(all_results):
    assert all_results["summary"]["quality_gain_hybrid_vs_auto"] >= 0


def test_run_all_strategy_comparison_matches_standalone(all_results):
    standalone = run_strategy_comparison(1_000)
    assert set(all_results["strategy_comparison"]["strategies"].keys()) == \
           set(standalone["strategies"].keys())