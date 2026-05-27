import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import threading
from services.rca.root_cause import RCAEngine
from services.rca.similarity import nearest_neighbours, similarity_clusters

engine = RCAEngine()

# ── progress bar ──────────────────────────────────────────────────────────
steps = ["Recording failures", "Running report", "Logging to MLflow", "Done"]

def _progress(i, label):
    pct = int(i / len(steps) * 40)
    print(f"\r[{'█' * pct}{'░' * (40 - pct)}] {i}/{len(steps)} {label:<25}", end="", flush=True)

# ── failures ──────────────────────────────────────────────────────────────
FAILURES = [
    ("e001", "standard",  "fraud",           "false_positive", 0.72, {"ml": {"risk_probability": 0.72}, "rule": {"risk_probability": 0.0}, "heuristic": {"signals": {"spam_patterns": 0.0}}},),
    ("e002", "expert",    "policy_violation", "false_negative", 0.55, {"ml": {"risk_probability": 0.55}, "rule": {"risk_probability": 0.3}, "heuristic": {"signals": {"spam_patterns": 0.1}}},),
    ("e003", "standard",  "fraud",           "false_positive", 0.68, {"ml": {"risk_probability": 0.68}, "rule": {"risk_probability": 0.0}, "heuristic": {"signals": {"spam_patterns": 0.0}}},),
    ("e004", "automated", "spam",            "false_negative", 0.40, {"ml": {"risk_probability": 0.40}, "rule": {"risk_probability": 0.0}, "heuristic": {"signals": {"spam_patterns": 0.6}}},),
    ("e005", "standard",  "fraud",           "reversal",       0.70, {"ml": {"risk_probability": 0.70}, "rule": {"risk_probability": 0.5}, "heuristic": {"signals": {"spam_patterns": 0.0}}},),
    ("e006", "standard",  "fraud",           "disagreement",   0.65, {"ml": {"risk_probability": 0.65}, "rule": {"risk_probability": 0.4}, "heuristic": {"signals": {"spam_patterns": 0.0}}}, "reviewer-42"),
]

_progress(0, "Starting...")

for f in FAILURES:
    reviewer_id = f[6] if len(f) > 6 else None
    engine.record_failure(
        event_id=f[0], tier=f[1], category=f[2], failure_type=f[3],
        risk_score=f[4], signals=f[5], reviewer_id=reviewer_id,
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

threading.Thread(target=_log, daemon=True).start()
_progress(3, steps[2])
print()

print(json.dumps(report, indent=2, default=str))