import os
import json
import logging
from datetime import datetime, timezone
from services.analytics.metrics       import QualityAnalyticsEngine
from services.analytics.comparison    import QualityCostComparator
from services.analytics.reporter      import ComparisonReporter
from services.rca.root_cause          import RCAEngine

logger = logging.getLogger(__name__)
OUTPUT_DIR = os.getenv("REPORT_OUTPUT_DIR", "reports")


class ReportGenerator:
    def __init__(
        self,
        quality_engine:  QualityAnalyticsEngine,
        rca_engine:      RCAEngine,
        total_events:    int = 10_000,
    ):
        self.quality  = quality_engine
        self.rca      = rca_engine
        self.reporter = ComparisonReporter()
        self.total    = total_events

    def generate(self) -> dict:
        snap    = self.quality.snapshot()
        gm      = snap["global_metrics"]
        rca_rep = self.rca.report()

        report = {
            "generated_at":   datetime.now(timezone.utc).isoformat(),
            "period":         "last_snapshot",
            "quality_summary": {
                "precision":           gm["precision"],
                "recall":              gm["recall"],
                "f1":                  gm["f1"],
                "false_positive_rate": gm["false_positive_rate"],
                "false_negative_rate": gm["false_negative_rate"],
                "escalation_rate":     snap["escalation"]["escalation_rate"],
                "reversal_rate":       snap["reversal"]["reversal_rate"],
                "by_tier":             snap["by_tier"],
                "by_category":         snap["by_category"],
            },
            "cost_summary":   self._cost_summary(),
            "rca_summary": {
                "total_failures":       rca_rep["total_failures"],
                "top_failure_modes":    list(rca_rep["failure_modes"].get("by_failure_type", {}).items())[:3],
                "emerging_categories":  rca_rep["emerging_categories"][:5],
                "drift_status":         rca_rep["trend"].get("status"),
            },
            "drift": self.quality.drift_report(),
        }
        return report

    def _cost_summary(self) -> dict:
        comparator = QualityCostComparator()
        comparison = comparator.compare_strategies(self.total)
        return {
            "recommended_strategy": comparison["recommended"],
            "strategies": {
                name: {
                    "total_cost":      data["total_cost"],
                    "quality_score":   data["quality_score"],
                    "efficiency_ratio": data["efficiency_ratio"],
                }
                for name, data in comparison["strategies"].items()
            },
        }

    def save(self, report: dict) -> str:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ts       = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(OUTPUT_DIR, f"report_{ts}.json")
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2, default=str)
        logger.info(f"Report saved: {filepath}")
        return filepath

    def print_summary(self, report: dict):
        qs = report["quality_summary"]
        cs = report["cost_summary"]
        rc = report["rca_summary"]
        print(f"""
╔══════════════════════════════════════════════════════╗
║        Adaptive Quality Platform — Report            ║
║        {report['generated_at'][:19]}                 ║
╠══════════════════════════════════════════════════════╣
║  Quality                                             ║
║    Precision : {qs['precision']:.4f}                         ║
║    Recall    : {qs['recall']:.4f}                         ║
║    F1        : {qs['f1']:.4f}                         ║
║    FPR       : {qs['false_positive_rate']:.4f}                         ║
║    FNR       : {qs['false_negative_rate']:.4f}                         ║
║    Escalation: {qs['escalation_rate']:.4f}                         ║
║    Reversals : {qs['reversal_rate']:.4f}                         ║
╠══════════════════════════════════════════════════════╣
║  Cost                                                ║
║    Recommended: {cs['recommended_strategy']:<36}║
╠══════════════════════════════════════════════════════╣
║  RCA                                                 ║
║    Total failures : {rc['total_failures']:<32}║
║    Drift status   : {rc['drift_status']:<32}║
╚══════════════════════════════════════════════════════╝
""")