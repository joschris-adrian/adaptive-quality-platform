import json
from services.rca.root_cause import RCAEngine

engine = RCAEngine()

# Seed with synthetic failures
FAILURES = [
    ("e001", "standard", "fraud",            "false_positive", 0.72, {"ml": {"risk_probability": 0.72}, "rule": {"risk_probability": 0.0}, "heuristic": {"signals": {"spam_patterns": 0.0}}}),
    ("e002", "expert",   "policy_violation",  "false_negative", 0.55, {"ml": {"risk_probability": 0.55}, "rule": {"risk_probability": 0.3}, "heuristic": {"signals": {"spam_patterns": 0.1}}}),
    ("e003", "standard", "fraud",            "false_positive", 0.68, {"ml": {"risk_probability": 0.68}, "rule": {"risk_probability": 0.0}, "heuristic": {"signals": {"spam_patterns": 0.0}}}),
    ("e004", "automated","spam",             "false_negative", 0.40, {"ml": {"risk_probability": 0.40}, "rule": {"risk_probability": 0.0}, "heuristic": {"signals": {"spam_patterns": 0.6}}}),
    ("e005", "standard", "fraud",            "reversal",       0.70, {"ml": {"risk_probability": 0.70}, "rule": {"risk_probability": 0.5}, "heuristic": {"signals": {"spam_patterns": 0.0}}}),
    ("e006", "standard", "fraud",            "disagreement",   0.65, {"ml": {"risk_probability": 0.65}, "rule": {"risk_probability": 0.4}, "heuristic": {"signals": {"spam_patterns": 0.0}}}, "reviewer-42"),
]

for f in FAILURES:
    reviewer_id = f[6] if len(f) > 6 else None
    engine.record_failure(
        event_id=f[0], tier=f[1], category=f[2], failure_type=f[3],
        risk_score=f[4], signals=f[5], reviewer_id=reviewer_id,
    )

report = engine.report()
print(json.dumps(report, indent=2, default=str))