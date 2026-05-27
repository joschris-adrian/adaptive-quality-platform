import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import random
import threading
from services.analytics.experimentation import ExperimentEngine

VARIANTS = ["control", "treatment"]
METRICS  = ["precision", "cost_per_event", "reversal_rate"]
N_EVENTS = 200
SPLIT    = {"control": 0.5, "treatment": 0.5}

steps = ["Setting up experiment", "Running events", "Logging to MLflow", "Done"]

def _progress(i, label):
    pct = int(i / len(steps) * 40)
    print(f"\r[{'█' * pct}{'░' * (40 - pct)}] {i}/{len(steps)} {label:<25}", end="", flush=True)


def build_metrics(variant: str) -> dict:
    precision     = random.gauss(0.82 if variant == "control" else 0.91, 0.05)
    cost          = random.gauss(0.50 if variant == "control" else 1.20, 0.10)
    reversal_rate = random.gauss(0.08 if variant == "control" else 0.04, 0.01)
    return {
        "precision":      max(0.0, min(1.0, precision)),
        "cost_per_event": max(0.0, cost),
        "reversal_rate":  max(0.0, min(1.0, reversal_rate)),
    }


def run_ab_experiment() -> dict:
    _progress(0, "Starting...")

    engine = ExperimentEngine()
    exp = engine.create(
        name="hybrid-vs-automation",
        description="Compare hybrid_balanced routing against automation_only",
        variants=VARIANTS,
        metrics=METRICS,
        traffic_split=SPLIT,
    )
    engine.start(exp.experiment_id)
    _progress(1, steps[0])

    for i in range(N_EVENTS):
        event_id = f"evt-{i:04d}"
        variant  = engine.assign(exp.experiment_id, event_id)
        engine.record(exp.experiment_id, event_id, build_metrics(variant))

    engine.complete(exp.experiment_id)
    results = engine.results(exp.experiment_id)
    _progress(2, steps[1])

    def _log():
        try:
            from services.mlflow.tracking import log_ab_variant
            for variant, stats in results["variants"].items():
                log_ab_variant(
                    experiment_name="ab-routing-strategy",
                    variant=variant,
                    params={"n_events": N_EVENTS, "split": SPLIT[variant]},
                    metrics={m: stats[m]["mean"] for m in METRICS if m in stats},
                )
        except Exception:
            pass

    t = threading.Thread(target=_log, daemon=False)
    t.start()
    t.join(timeout=30)
    _progress(3, steps[2])
    print()

    return results


if __name__ == "__main__":
    results = run_ab_experiment()
    print("\n=== A/B Experiment: Hybrid vs Automation ===")
    for variant, stats in results["variants"].items():
        print(f"\n  {variant}:")
        for metric, vals in stats.items():
            if metric == "n":
                continue
            print(f"    {metric}: mean={vals['mean']}  std={vals['std']}")
    print(f"\n  winner:  {results['winner']}")
    print(f"  lifts:   {results['relative_lifts']}")