from services.analytics.comparison import QualityCostComparator


class ComparisonReporter:
    def __init__(self, comparator: QualityCostComparator = None):
        self.comparator = comparator or QualityCostComparator()

    def strategy_summary(self, total_events: int) -> str:
        report = self.comparator.compare_strategies(total_events)
        lines  = [
            f"Quality vs Cost Comparison — {total_events:,} events",
            "=" * 60,
            f"{'Strategy':<25} {'Cost':>10} {'Accuracy':>10} {'Efficiency':>12}",
            "-" * 60,
        ]
        for name, data in report["strategies"].items():
            marker = " ◄ recommended" if name == report["recommended"] else ""
            lines.append(
                f"{name:<25} "
                f"${data['total_cost']:>9,.2f} "
                f"{data['system_accuracy']:>9.1%} "
                f"{data['efficiency_ratio']:>12.6f}"
                f"{marker}"
            )
        lines += [
            "-" * 60,
            f"Recommended: {report['recommended']}",
        ]
        return "\n".join(lines)

    def threshold_table(self, total_events: int) -> str:
        rows  = self.comparator.threshold_sensitivity(total_events)
        lines = [
            f"Threshold Sensitivity — {total_events:,} events",
            "=" * 70,
            f"{'Threshold':>10} {'Auto%':>7} {'Std%':>7} {'Exp%':>7} "
            f"{'Cost':>10} {'Accuracy':>10} {'Quality':>9}",
            "-" * 70,
        ]
        for r in rows:
            sp = r["tier_split"]
            lines.append(
                f"{r['escalate_threshold']:>10.2f} "
                f"{sp['automated']:>6.0%} "
                f"{sp['standard']:>6.0%} "
                f"{sp['expert']:>6.0%} "
                f"${r['total_cost']:>9,.2f} "
                f"{r['system_accuracy']:>9.1%} "
                f"{r['quality_score']:>9.4f}"
            )
        return "\n".join(lines)

    def budget_report(self, total_events: int, budget: float) -> str:
        affordable = self.comparator.cost_under_budget(total_events, budget)
        lines = [
            f"Strategies within budget ${budget:,.2f} — {total_events:,} events",
            "=" * 55,
        ]
        if not affordable:
            lines.append("No strategies fit within this budget.")
        else:
            for s in affordable:
                lines.append(
                    f"  {s['name']:<25} cost=${s['total_cost']:,.2f} "
                    f"quality={s['quality_score']:.4f}"
                )
        return "\n".join(lines)