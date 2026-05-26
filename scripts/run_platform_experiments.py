import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.analytics.comparison     import QualityCostComparator, STRATEGIES
from services.analytics.experimentation import ExperimentEngine

TOTAL_EVENTS = 10_000
BUDGET       = 3_000.0


def run_strategy_comparison(total_events: int) -> dict:
    comparator = QualityCostComparator()
    result     = comparator.compare_strategies(total_events)
    result["total_events"] = total_events
    return result


def run_threshold_sweep(
    total_events: int,
    thresholds:   list[float] = None,
) -> dict:
    thresholds = thresholds or [0.50, 0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
    engine     = ExperimentEngine()
    return engine.threshold_experiment(
        name="exp3-threshold-sweep",
        thresholds=thresholds,
        total_events=total_events,
    )


def run_budget_experiment(total_events: int, budget: float) -> list:
    comparator = QualityCostComparator()
    return comparator.cost_under_budget(total_events, budget)


def run_all(
    total_events: int = TOTAL_EVENTS,
    budget:       float = BUDGET,
) -> dict:
    strategy   = run_strategy_comparison(total_events)
    threshold  = run_threshold_sweep(total_events)
    affordable = run_budget_experiment(total_events, budget)

    strategies = strategy["strategies"]
    auto       = strategies["automation_only"]
    hybrid     = strategies["hybrid_balanced"]

    return {
        "strategy_comparison": strategy,
        "threshold_sweep":     threshold,
        "budget_experiment":   affordable,
        "summary": {
            "quality_gain_hybrid_vs_auto":  round(
                hybrid["quality_score"] - auto["quality_score"], 4
            ),
            "cost_increase_hybrid_vs_auto": round(
                hybrid["total_cost"] - auto["total_cost"], 2
            ),
            "optimal_threshold":            threshold["optimal"]["escalate_threshold"],
            "best_affordable_strategy":     affordable[0]["name"] if affordable else None,
        },
    }


if __name__ == "__main__":
    results = run_all()

    print("=" * 65)
    print("Experiments 1 & 2 — Strategy Comparison")
    print("=" * 65)
    comp = results["strategy_comparison"]
    print(f"{'Strategy':<25} {'Cost':>10} {'Quality':>10} {'Efficiency':>12}")
    print("-" * 65)
    for name, data in comp["strategies"].items():
        marker = " ◄" if name == comp["recommended"] else ""
        print(
            f"{name:<25} "
            f"${data['total_cost']:>9,.0f} "
            f"{data['quality_score']:>10.4f} "
            f"{data['efficiency_ratio']:>12.6f}"
            f"{marker}"
        )

    print("\n" + "=" * 65)
    print("Experiment 3 — Threshold Sweep")
    print("=" * 65)
    print(f"{'Threshold':>10} {'Cost':>10} {'Quality':>10} {'Auto%':>7}")
    print("-" * 45)
    for row in results["threshold_sweep"]["results"]:
        sp = row["tier_split"]
        print(
            f"{row['escalate_threshold']:>10.2f} "
            f"${row['total_cost']:>9,.0f} "
            f"{row['quality_score']:>10.4f} "
            f"{sp['automated']:>6.0%}"
        )

    print("\n" + "=" * 65)
    print(f"Experiment 4 — Budget=${BUDGET:,.0f}")
    print("=" * 65)
    for s in results["budget_experiment"]:
        print(
            f"  {s['name']:<25} "
            f"${s['total_cost']:>9,.0f}  "
            f"quality={s['quality_score']:.4f}"
        )

    print("\n" + "=" * 65)
    print("Summary")
    print("=" * 65)
    sm = results["summary"]
    print(f"Quality gain (hybrid vs auto):  +{sm['quality_gain_hybrid_vs_auto']:.4f}")
    print(f"Cost increase (hybrid vs auto): +${sm['cost_increase_hybrid_vs_auto']:,.0f}")
    print(f"Optimal threshold:               {sm['optimal_threshold']}")
    print(f"Best affordable strategy:        {sm['best_affordable_strategy']}")