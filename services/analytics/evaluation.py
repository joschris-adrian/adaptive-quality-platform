from dataclasses import dataclass, field
from typing import Optional
from collections import defaultdict


@dataclass
class EvaluationResult:
    # Quality
    precision:           float
    recall:              float
    f1:                  float
    false_positive_rate: float
    false_negative_rate: float
    accuracy:            float
    # Operational
    avg_queue_latency_ms:  float
    p95_queue_latency_ms:  float
    throughput_per_second: float
    resource_utilisation:  float   # 0.0–1.0
    # Business
    cost_per_reviewed_event:  float
    high_risk_capture_rate:   float
    escalation_efficiency:    float
    # Counts
    total_decisions:   int
    total_labelled:    int
    support:           dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "quality": {
                "precision":           round(self.precision,           4),
                "recall":              round(self.recall,              4),
                "f1":                  round(self.f1,                  4),
                "false_positive_rate": round(self.false_positive_rate, 4),
                "false_negative_rate": round(self.false_negative_rate, 4),
                "accuracy":            round(self.accuracy,            4),
            },
            "operational": {
                "avg_queue_latency_ms":  round(self.avg_queue_latency_ms,  2),
                "p95_queue_latency_ms":  round(self.p95_queue_latency_ms,  2),
                "throughput_per_second": round(self.throughput_per_second, 2),
                "resource_utilisation":  round(self.resource_utilisation,  4),
            },
            "business": {
                "cost_per_reviewed_event": round(self.cost_per_reviewed_event, 4),
                "high_risk_capture_rate":  round(self.high_risk_capture_rate,  4),
                "escalation_efficiency":   round(self.escalation_efficiency,   4),
            },
            "counts": {
                "total_decisions": self.total_decisions,
                "total_labelled":  self.total_labelled,
                "support":         self.support,
            },
        }


class QualityMetricsCalculator:

    def compute(
        self,
        tp: int, fp: int, tn: int, fn: int,
    ) -> dict:
        precision = tp / (tp + fp) if (tp + fp) else 0.0
        recall    = tp / (tp + fn) if (tp + fn) else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) else 0.0)
        fpr       = fp / (fp + tn) if (fp + tn) else 0.0
        fnr       = fn / (fn + tp) if (fn + tp) else 0.0
        accuracy  = (tp + tn) / (tp + fp + tn + fn) if (tp + fp + tn + fn) else 0.0

        return {
            "precision":           round(precision, 4),
            "recall":              round(recall,    4),
            "f1":                  round(f1,        4),
            "false_positive_rate": round(fpr,       4),
            "false_negative_rate": round(fnr,       4),
            "accuracy":            round(accuracy,  4),
            "tp": tp, "fp": fp, "tn": tn, "fn": fn,
        }

    def error_rate(self, tp: int, fp: int, tn: int, fn: int) -> float:
        total = tp + fp + tn + fn
        return round((fp + fn) / total, 4) if total else 0.0

    def compute_by_category(
        self,
        records: list[dict],   # each: {category, predicted, ground_truth}
    ) -> dict[str, dict]:
        buckets: dict[str, dict] = defaultdict(
            lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
        )
        for r in records:
            cat = r["category"]
            p   = r["predicted"]
            g   = r["ground_truth"]
            if   p == "positive" and g == "positive": buckets[cat]["tp"] += 1
            elif p == "positive" and g == "negative": buckets[cat]["fp"] += 1
            elif p == "negative" and g == "negative": buckets[cat]["tn"] += 1
            elif p == "negative" and g == "positive": buckets[cat]["fn"] += 1

        return {
            cat: self.compute(**counts)
            for cat, counts in buckets.items()
        }

    def macro_average(self, per_category: dict[str, dict]) -> dict:
        if not per_category:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        keys = ["precision", "recall", "f1",
                "false_positive_rate", "false_negative_rate", "accuracy"]
        return {
            k: round(
                sum(cat[k] for cat in per_category.values()) / len(per_category),
                4,
            )
            for k in keys
        }

    def weighted_average(self, per_category: dict[str, dict]) -> dict:
        if not per_category:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}
        total_support = sum(
            cat["tp"] + cat["fp"] + cat["tn"] + cat["fn"]
            for cat in per_category.values()
        )
        if not total_support:
            return {"precision": 0.0, "recall": 0.0, "f1": 0.0}

        keys = ["precision", "recall", "f1",
                "false_positive_rate", "false_negative_rate", "accuracy"]
        result = {}
        for k in keys:
            weighted_sum = sum(
                cat[k] * (cat["tp"] + cat["fp"] + cat["tn"] + cat["fn"])
                for cat in per_category.values()
            )
            result[k] = round(weighted_sum / total_support, 4)
        return result


class OperationalMetricsCalculator:

    def queue_latency(self, latencies_ms: list[float]) -> dict:
        if not latencies_ms:
            return {
                "avg_ms": 0.0, "p50_ms": 0.0,
                "p95_ms": 0.0, "p99_ms": 0.0,
                "min_ms": 0.0, "max_ms": 0.0,
            }
        sorted_l = sorted(latencies_ms)
        n        = len(sorted_l)

        def percentile(p: float) -> float:
            idx = int(p / 100 * n)
            return round(sorted_l[min(idx, n - 1)], 2)

        return {
            "avg_ms": round(sum(latencies_ms) / n, 2),
            "p50_ms": percentile(50),
            "p95_ms": percentile(95),
            "p99_ms": percentile(99),
            "min_ms": round(sorted_l[0],  2),
            "max_ms": round(sorted_l[-1], 2),
        }

    def throughput(
        self,
        total_events: int,
        elapsed_seconds: float,
    ) -> float:
        return round(total_events / elapsed_seconds, 2) if elapsed_seconds else 0.0

    def resource_utilisation(
        self,
        cpu_pct:    float,
        memory_pct: float,
        cpu_weight: float = 0.6,
        mem_weight: float = 0.4,
    ) -> float:
        score = cpu_pct * cpu_weight + memory_pct * mem_weight
        return round(min(score / 100, 1.0), 4)

    def queue_backlog_health(
        self,
        pending:           int,
        capacity_limit:    int,
        oldest_pending_ms: float,
        sla_ms:            float,
    ) -> dict:
        queue_pct  = round(pending / capacity_limit, 4) if capacity_limit else 0.0
        sla_breach = oldest_pending_ms > sla_ms

        if queue_pct >= 0.90 or sla_breach:
            status = "critical"
        elif queue_pct >= 0.70:
            status = "warning"
        else:
            status = "healthy"

        return {
            "pending":           pending,
            "capacity_limit":    capacity_limit,
            "queue_pct":         queue_pct,
            "oldest_pending_ms": oldest_pending_ms,
            "sla_ms":            sla_ms,
            "sla_breach":        sla_breach,
            "status":            status,
        }


class BusinessMetricsCalculator:

    def cost_per_reviewed_event(
        self,
        total_cost:      float,
        reviewed_events: int,
    ) -> float:
        return round(total_cost / reviewed_events, 4) if reviewed_events else 0.0

    def high_risk_capture_rate(
        self,
        high_risk_correctly_escalated: int,
        total_high_risk:               int,
    ) -> float:
        return round(
            high_risk_correctly_escalated / total_high_risk, 4
        ) if total_high_risk else 0.0

    def escalation_efficiency(
        self,
        true_positives_escalated: int,
        total_escalated:          int,
    ) -> float:
        """Fraction of escalated events that were genuine positives."""
        return round(
            true_positives_escalated / total_escalated, 4
        ) if total_escalated else 0.0

    def cost_per_correct_decision(
        self,
        total_cost:       float,
        correct_decisions: int,
    ) -> float:
        return round(
            total_cost / correct_decisions, 4
        ) if correct_decisions else 0.0

    def roi(
        self,
        value_of_caught_events: float,
        total_cost:             float,
    ) -> float:
        """(value captured - cost) / cost."""
        if not total_cost:
            return 0.0
        return round((value_of_caught_events - total_cost) / total_cost, 4)

    def false_negative_business_cost(
        self,
        fn_count:          int,
        cost_per_miss:     float,
    ) -> float:
        """Estimated business cost of missed high-risk events."""
        return round(fn_count * cost_per_miss, 4)


class EvaluationSuite:
    """
    Combines all three metric calculators into a single evaluation run.
    """

    def __init__(self):
        self.quality     = QualityMetricsCalculator()
        self.operational = OperationalMetricsCalculator()
        self.business    = BusinessMetricsCalculator()

    def evaluate(
        self,
        tp: int, fp: int, tn: int, fn: int,
        latencies_ms:        list[float],
        elapsed_seconds:     float,
        cpu_pct:             float,
        memory_pct:          float,
        total_cost:          float,
        reviewed_events:     int,
        high_risk_escalated: int,
        total_high_risk:     int,
        total_escalated:     int,
    ) -> EvaluationResult:
        q    = self.quality.compute(tp, fp, tn, fn)
        lat  = self.operational.queue_latency(latencies_ms)
        util = self.operational.resource_utilisation(cpu_pct, memory_pct)
        tput = self.operational.throughput(tp + fp + tn + fn, elapsed_seconds)
        cpre = self.business.cost_per_reviewed_event(total_cost, reviewed_events)
        hrcr = self.business.high_risk_capture_rate(high_risk_escalated, total_high_risk)
        eff  = self.business.escalation_efficiency(tp, total_escalated)

        return EvaluationResult(
            precision=           q["precision"],
            recall=              q["recall"],
            f1=                  q["f1"],
            false_positive_rate= q["false_positive_rate"],
            false_negative_rate= q["false_negative_rate"],
            accuracy=            q["accuracy"],
            avg_queue_latency_ms=  lat["avg_ms"],
            p95_queue_latency_ms=  lat["p95_ms"],
            throughput_per_second= tput,
            resource_utilisation=  util,
            cost_per_reviewed_event=  cpre,
            high_risk_capture_rate=   hrcr,
            escalation_efficiency=    eff,
            total_decisions= tp + fp + tn + fn,
            total_labelled=  tp + fp + tn + fn,
            support={
                "tp": tp, "fp": fp, "tn": tn, "fn": fn,
            },
        )

    def compare(
        self,
        baseline:  EvaluationResult,
        treatment: EvaluationResult,
    ) -> dict:
        def lift(b: float, t: float) -> Optional[float]:
            return round((t - b) / abs(b) * 100, 2) if b != 0 else None

        return {
            "quality_lifts": {
                "precision": lift(baseline.precision, treatment.precision),
                "recall":    lift(baseline.recall,    treatment.recall),
                "f1":        lift(baseline.f1,        treatment.f1),
            },
            "operational_lifts": {
                "throughput":     lift(
                    baseline.throughput_per_second,
                    treatment.throughput_per_second,
                ),
                "avg_latency_ms": lift(
                    baseline.avg_queue_latency_ms,
                    treatment.avg_queue_latency_ms,
                ),
            },
            "business_lifts": {
                "cost_per_reviewed": lift(
                    baseline.cost_per_reviewed_event,
                    treatment.cost_per_reviewed_event,
                ),
                "high_risk_capture": lift(
                    baseline.high_risk_capture_rate,
                    treatment.high_risk_capture_rate,
                ),
            },
            "winner": self._pick_winner(baseline, treatment),
        }

    def _pick_winner(
        self,
        baseline:  EvaluationResult,
        treatment: EvaluationResult,
    ) -> str:
        b_score = baseline.f1  * 0.5 + baseline.high_risk_capture_rate * 0.3 \
                - baseline.cost_per_reviewed_event * 0.2
        t_score = treatment.f1 * 0.5 + treatment.high_risk_capture_rate * 0.3 \
                - treatment.cost_per_reviewed_event * 0.2
        return "treatment" if t_score > b_score else "baseline"