import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import threading
from services.rca.root_cause import RCAEngine
from services.rca.similarity import nearest_neighbours, similarity_clusters

engine = RCAEngine()

steps = ["Recording failures", "Running report", "Logging to MLflow", "Done"]

def _progress(i, label):
    pct = int(i / len(steps) * 40)
    print(f"\r[{'█' * pct}{'░' * (40 - pct)}] {i}/{len(steps)} {label:<25}", end="", flush=True)

FAILURES = [
    {
        "event_id":    "f001",
        "tier":        "standard",
        "category":    "fraud",
        "failure_type": "false_positive",
        "risk_score":  0.72,
        "signals": {
            "ml":        {"risk_probability": 0.72},
            "rule":      {"risk_probability": 0.00, "rules_triggered": []},
            "heuristic": {"signals": {"spam_patterns": 0.0, "velocity": 0.3}},
        },
    },
    {
        "event_id":    "f002",
        "tier":        "expert",
        "category":    "policy_violation",
        "failure_type": "false_negative",
        "risk_score":  0.55,
        "signals": {
            "ml":        {"risk_probability": 0.55},
            "rule":      {"risk_probability": 0.30, "rules_triggered": []},
            "heuristic": {"signals": {"spam_patterns": 0.1, "velocity": 0.0}},
        },
    },
    {
        "event_id":    "f003",
        "tier":        "standard",
        "category":    "fraud",
        "failure_type": "false_positive",
        "risk_score":  0.68,
        "signals": {
            "ml":        {"risk_probability": 0.68},
            "rule":      {"risk_probability": 0.00, "rules_triggered": []},
            "heuristic": {"signals": {"spam_patterns": 0.0, "velocity": 0.3}},
        },
    },
    {
        "event_id":    "f004",
        "tier":        "automated",
        "category":    "spam",
        "failure_type": "false_negative",
        "risk_score":  0.40,
        "signals": {
            "ml":        {"risk_probability": 0.40},
            "rule":      {"risk_probability": 0.00, "rules_triggered": []},
            "heuristic": {"signals": {"spam_patterns": 0.6, "velocity": 0.0}},
        },
    },
    {
        "event_id":    "f005",
        "tier":        "standard",
        "category":    "fraud",
        "failure_type": "reversal",
        "risk_score":  0.70,
        "signals": {
            "ml":        {"risk_probability": 0.70},
            "rule":      {"risk_probability": 0.50, "rules_triggered": ["high_risk_hint"]},
            "heuristic": {"signals": {"spam_patterns": 0.0, "velocity": 0.3}},
        },
    },
    {
        "event_id":    "f006",
        "tier":        "standard",
        "category":    "fraud",
        "failure_type": "disagreement",
        "risk_score":  0.65,
        "reviewer_id": "reviewer-42",
        "signals": {
            "ml":        {"risk_probability": 0.65},
            "rule":      {"risk_probability": 0.40, "rules_triggered": []},
            "heuristic": {"signals": {"spam_patterns": 0.0, "velocity": 0.3}},
        },
    },
]

_progress(0, "Starting...")

for f in FAILURES:
    engine.record_failure(
        event_id=     f["event_id"],
        tier=         f["tier"],
        category=     f["category"],
        failure_type= f["failure_type"],
        risk_score=   f["risk_score"],
        signals=      f["signals"],
        reviewer_id=  f.get("reviewer_id"),
    )

_progress(1, steps[0])

report = engine.report()

_progress(2, steps[1])

def _log():
    try:
        from services.mlflow.tracking import log_drift_snapshot
        log_drift_snapshot(report["trend"])
    except Exception:
        pass

t = threading.Thread(target=_log, daemon=False)
t.start()
t.join(timeout=30)
_progress(3, steps[2])
print()

print("=" * 60)
print("RCA Report")
print("=" * 60)
print(f"\nTotal failures: {report['total_failures']}")

print("\nFailure modes:")
for ftype, data in report["failure_modes"]["by_failure_type"].items():
    print(f"  {ftype:<20} count={data['count']}  rate={data['rate']:.2%}")

print("\nBy category:")
for cat, data in report["failure_modes"]["by_category"].items():
    print(f"  {cat:<20} count={data['count']}  rate={data['rate']:.2%}")

print("\nSignal correlation (mean on failures):")
for sig, data in report["signal_correlation"].items():
    print(f"  {sig:<40} mean={data['mean_on_failures']}")

print("\nClusters (category × failure type):")
for cluster, data in report["clusters"].items():
    print(f"  {cluster:<35} count={data['count']}  "
          f"avg_risk={data['avg_risk_score']}")

print("\nDisagreement patterns:")
dp = report["disagreement"]
print(f"  Total disagreements: {dp['total_disagreements']}")
if dp["by_reviewer"]:
    for rev, data in dp["by_reviewer"].items():
        print(f"  Reviewer {rev}: {data['count']} disagreements")

print(f"\nDrift status: {report['trend'].get('status', 'insufficient_data')}")
print(f"Emerging categories: {report['emerging_categories']}")

print("\nFull report (JSON):")
print(json.dumps(report, indent=2, default=str))