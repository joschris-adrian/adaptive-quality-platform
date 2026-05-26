from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Callable
from collections import defaultdict
import random
import uuid


@dataclass
class Experiment:
    experiment_id:   str
    name:            str
    description:     str
    variants:        list[str]          # e.g. ["control", "treatment_a", "treatment_b"]
    metrics:         list[str]          # metrics to track e.g. ["precision", "cost", "reversal_rate"]
    traffic_split:   dict[str, float]   # variant -> fraction, must sum to 1.0
    status:          str = "draft"      # draft | running | paused | completed
    created_at:      datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at:      Optional[datetime] = None
    completed_at:    Optional[datetime] = None
    metadata:        dict = field(default_factory=dict)


@dataclass
class ExperimentObservation:
    experiment_id: str
    variant:       str
    event_id:      str
    metrics:       dict[str, float]    # metric_name -> value
    timestamp:     datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ExperimentEngine:
    def __init__(self):
        self._experiments:   dict[str, Experiment]                         = {}
        self._observations:  dict[str, list[ExperimentObservation]]        = defaultdict(list)
        self._assignments:   dict[str, dict[str, str]]                     = defaultdict(dict)
        # _assignments[experiment_id][event_id] = variant

    # ── Experiment lifecycle ───────────────────────────────────────────────

    def create(
        self,
        name:          str,
        description:   str,
        variants:      list[str],
        metrics:       list[str],
        traffic_split: dict[str, float] = None,
        metadata:      dict = None,
    ) -> Experiment:
        if traffic_split is None:
            share = round(1.0 / len(variants), 6)
            traffic_split = {v: share for v in variants}

        total = sum(traffic_split.values())
        if abs(total - 1.0) > 1e-4:
            raise ValueError(f"traffic_split must sum to 1.0, got {total:.4f}")

        if set(traffic_split.keys()) != set(variants):
            raise ValueError("traffic_split keys must match variants")

        experiment_id = str(uuid.uuid4())
        exp = Experiment(
            experiment_id=experiment_id,
            name=name,
            description=description,
            variants=variants,
            metrics=metrics,
            traffic_split=traffic_split,
            metadata=metadata or {},
        )
        self._experiments[experiment_id] = exp
        return exp

    def start(self, experiment_id: str) -> Experiment:
        exp = self._get(experiment_id)
        if exp.status not in ("draft", "paused"):
            raise ValueError(f"Cannot start experiment in status '{exp.status}'")
        exp.status     = "running"
        exp.started_at = datetime.now(timezone.utc)
        return exp

    def pause(self, experiment_id: str) -> Experiment:
        exp = self._get(experiment_id)
        if exp.status != "running":
            raise ValueError(f"Cannot pause experiment in status '{exp.status}'")
        exp.status = "paused"
        return exp

    def complete(self, experiment_id: str) -> Experiment:
        exp = self._get(experiment_id)
        exp.status       = "completed"
        exp.completed_at = datetime.now(timezone.utc)
        return exp

    # ── Assignment ────────────────────────────────────────────────────────

    def assign(self, experiment_id: str, event_id: str) -> str:
        """
        Deterministically assign an event to a variant using hash-based
        bucketing so the same event always gets the same variant.
        """
        exp = self._get(experiment_id)
        if exp.status != "running":
            raise ValueError(f"Experiment '{experiment_id}' is not running")

        if event_id in self._assignments[experiment_id]:
            return self._assignments[experiment_id][event_id]

        bucket   = int(uuid.UUID(event_id).int if self._is_uuid(event_id)
                       else abs(hash(event_id))) % 10000 / 10000
        cumulative = 0.0
        variant    = exp.variants[-1]

        for v, share in exp.traffic_split.items():
            cumulative += share
            if bucket < cumulative:
                variant = v
                break

        self._assignments[experiment_id][event_id] = variant
        return variant

    def assign_random(self, experiment_id: str, event_id: str) -> str:
        """Non-deterministic assignment — useful for synthetic load tests."""
        exp = self._get(experiment_id)
        if exp.status != "running":
            raise ValueError(f"Experiment '{experiment_id}' is not running")

        roll    = random.random()
        cumulative = 0.0
        variant = exp.variants[-1]
        for v, share in exp.traffic_split.items():
            cumulative += share
            if roll < cumulative:
                variant = v
                break

        self._assignments[experiment_id][event_id] = variant
        return variant

    # ── Observation recording ─────────────────────────────────────────────

    def record(
        self,
        experiment_id: str,
        event_id:      str,
        metrics:       dict[str, float],
    ):
        variant = self._assignments.get(experiment_id, {}).get(event_id)
        if not variant:
            raise KeyError(
                f"event_id '{event_id}' has no assignment in experiment '{experiment_id}'"
            )
        obs = ExperimentObservation(
            experiment_id=experiment_id,
            variant=variant,
            event_id=event_id,
            metrics=metrics,
        )
        self._observations[experiment_id].append(obs)

    # ── Analysis ──────────────────────────────────────────────────────────

    def results(self, experiment_id: str) -> dict:
        exp          = self._get(experiment_id)
        observations = self._observations[experiment_id]

        if not observations:
            return {"experiment_id": experiment_id, "status": exp.status, "variants": {}}

        by_variant: dict[str, list[ExperimentObservation]] = defaultdict(list)
        for obs in observations:
            by_variant[obs.variant].append(obs)

        variant_stats = {}
        for variant, obs_list in by_variant.items():
            variant_stats[variant] = self._summarise(obs_list, exp.metrics)

        return {
            "experiment_id": experiment_id,
            "name":          exp.name,
            "status":        exp.status,
            "total_observations": len(observations),
            "variants":      variant_stats,
            "winner":        self._pick_winner(variant_stats, exp.metrics),
            "relative_lifts": self._relative_lifts(variant_stats, exp.metrics),
        }

    def _summarise(
        self,
        observations: list[ExperimentObservation],
        metrics:      list[str],
    ) -> dict:
        n = len(observations)
        stats = {"n": n}
        for metric in metrics:
            values = [
                obs.metrics[metric]
                for obs in observations
                if metric in obs.metrics
            ]
            if not values:
                stats[metric] = {"mean": None, "min": None, "max": None, "std": None}
                continue
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            stats[metric] = {
                "mean":   round(mean, 4),
                "min":    round(min(values), 4),
                "max":    round(max(values), 4),
                "std":    round(variance ** 0.5, 4),
                "n":      len(values),
            }
        return stats

    def _pick_winner(self, variant_stats: dict, metrics: list[str]) -> Optional[str]:
        """
        Pick the variant with the best mean on the first metric in the list.
        Higher is better for quality metrics; lower is better for cost metrics.
        """
        if not metrics or not variant_stats:
            return None

        primary      = metrics[0]
        lower_better = primary in ("cost", "reversal_rate", "false_positive_rate",
                                   "false_negative_rate", "latency_ms")
        candidates = {
            v: stats[primary]["mean"]
            for v, stats in variant_stats.items()
            if stats.get(primary, {}).get("mean") is not None
        }
        if not candidates:
            return None

        return min(candidates, key=candidates.get) if lower_better \
               else max(candidates, key=candidates.get)

    def _relative_lifts(
        self,
        variant_stats: dict,
        metrics:       list[str],
    ) -> dict:
        """
        For each non-control variant, compute % lift vs control on each metric.
        Falls back to first variant as baseline if no 'control' variant exists.
        """
        baseline_key = "control" if "control" in variant_stats else \
                       next(iter(variant_stats), None)
        if not baseline_key:
            return {}

        baseline = variant_stats[baseline_key]
        lifts    = {}

        for variant, stats in variant_stats.items():
            if variant == baseline_key:
                continue
            variant_lifts = {}
            for metric in metrics:
                base_mean    = baseline.get(metric, {}).get("mean")
                variant_mean = stats.get(metric, {}).get("mean")
                if base_mean is not None and variant_mean is not None and base_mean != 0:
                    pct = (variant_mean - base_mean) / abs(base_mean) * 100
                    variant_lifts[metric] = round(pct, 2)
                else:
                    variant_lifts[metric] = None
            lifts[variant] = variant_lifts

        return lifts

    # ── Built-in experiment templates ─────────────────────────────────────

    def threshold_experiment(
        self,
        name:         str,
        thresholds:   list[float],
        total_events: int,
    ) -> dict:
        """
        Simulate how different escalation thresholds affect cost and quality
        without needing live traffic. Returns per-threshold stats.
        """
        from services.analytics.comparison import QualityCostComparator
        comparator = QualityCostComparator()
        rows       = comparator.threshold_sensitivity(
            total_events, escalate_thresholds=thresholds
        )
        return {
            "name":       name,
            "type":       "threshold_sensitivity",
            "thresholds": thresholds,
            "results":    rows,
            "optimal":    min(rows, key=lambda r: -r["quality_score"] + r["total_cost"] / 10_000),
        }

    def routing_strategy_experiment(
        self,
        name:         str,
        total_events: int,
        budget:       Optional[float] = None,
    ) -> dict:
        """
        Compare all built-in routing strategies by quality and cost.
        Optionally filter to strategies within a budget.
        """
        from services.analytics.comparison import QualityCostComparator, STRATEGIES
        comparator = QualityCostComparator()

        if budget:
            strategies = comparator.cost_under_budget(total_events, budget)
            return {
                "name":        name,
                "type":        "routing_strategy",
                "total_events": total_events,
                "budget":      budget,
                "results":     strategies,
            }

        comparison = comparator.compare_strategies(total_events)
        return {
            "name":        name,
            "type":        "routing_strategy",
            "total_events": total_events,
            "results":     comparison["strategies"],
            "recommended": comparison["recommended"],
        }

    def label_quality_experiment(
        self,
        name:              str,
        event_ids:         list[str],
        labeller_a_fn:     Callable[[str], str],
        labeller_b_fn:     Callable[[str], str],
    ) -> dict:
        """
        Compare two labelling functions (or reviewer groups) on the same
        set of events. Returns agreement rate and per-label breakdown.
        """
        agreements   = 0
        disagreements = 0
        label_pairs: list[tuple[str, str]] = []

        for eid in event_ids:
            label_a = labeller_a_fn(eid)
            label_b = labeller_b_fn(eid)
            label_pairs.append((label_a, label_b))
            if label_a == label_b:
                agreements += 1
            else:
                disagreements += 1

        total = len(event_ids)
        return {
            "name":             name,
            "type":             "label_quality",
            "total":            total,
            "agreement_rate":   round(agreements   / total, 4) if total else 0.0,
            "disagreement_rate": round(disagreements / total, 4) if total else 0.0,
            "agreements":       agreements,
            "disagreements":    disagreements,
        }

    def sampling_experiment(
        self,
        name:          str,
        population:    list[dict],
        sample_rates:  list[float],
        metric_fn:     Callable[[list[dict]], float],
    ) -> list[dict]:
        """
        For each sample rate, draw a random sample from population,
        compute a metric, and return how metric changes with sample size.
        Useful for calibrating review sampling strategies.
        """
        results = []
        for rate in sample_rates:
            k      = max(1, int(len(population) * rate))
            sample = random.sample(population, k)
            metric = metric_fn(sample)
            results.append({
                "sample_rate":  rate,
                "sample_size":  k,
                "metric_value": round(metric, 4),
            })
        return results

    # ── Helpers ───────────────────────────────────────────────────────────

    def _get(self, experiment_id: str) -> Experiment:
        if experiment_id not in self._experiments:
            raise KeyError(f"Experiment '{experiment_id}' not found")
        return self._experiments[experiment_id]

    def _is_uuid(self, s: str) -> bool:
        try:
            uuid.UUID(s)
            return True
        except ValueError:
            return False

    def list_experiments(self, status: Optional[str] = None) -> list[Experiment]:
        exps = list(self._experiments.values())
        if status:
            exps = [e for e in exps if e.status == status]
        return sorted(exps, key=lambda e: e.created_at, reverse=True)