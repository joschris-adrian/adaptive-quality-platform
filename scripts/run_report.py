import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.analytics.metrics  import QualityAnalyticsEngine
from services.rca.root_cause     import RCAEngine
from dashboards.report_generator import ReportGenerator

# ── seed quality engine ────────────────────────────────────────────────────

quality = QualityAnalyticsEngine()

# 40 true positives
for i in range(40):
    quality.record_decision(f"e{i}", "standard", "fraud", "positive", 0.82, escalated=True)
    quality.record_ground_truth(f"e{i}", "positive")

# 10 false positives
for i in range(40, 50):
    quality.record_decision(f"e{i}", "standard", "spam", "positive", 0.65, escalated=False)
    quality.record_ground_truth(f"e{i}", "negative")

# 30 true negatives
for i in range(50, 80):
    quality.record_decision(f"e{i}", "automated", "clean", "negative", 0.15, escalated=False)
    quality.record_ground_truth(f"e{i}", "negative")

# 20 false negatives
for i in range(80, 100):
    quality.record_decision(f"e{i}", "automated", "fraud", "negative", 0.35, escalated=False)
    quality.record_ground_truth(f"e{i}", "positive")

# 5 reversals
for i in range(100, 105):
    quality.record_decision(f"e{i}", "expert", "fraud", "positive", 0.78, escalated=True)
    quality.record_reversal(f"e{i}")

# ── seed RCA engine ────────────────────────────────────────────────────────

rca = RCAEngine()

SIGNALS = {
    "ml":        {"risk_probability": 0.72},
    "rule":      {"risk_probability": 0.30, "rules_triggered": []},
    "heuristic": {"signals": {"spam_patterns": 0.1, "velocity": 0.2}},
}

FAILURES = [
    ("f001", "standard", "fraud",            "false_positive", 0.72),
    ("f002", "expert",   "policy_violation",  "false_negative", 0.55),
    ("f003", "standard", "fraud",            "false_positive", 0.68),
    ("f004", "automated","spam",             "false_negative", 0.40),
    ("f005", "standard", "fraud",            "reversal",       0.70),
    ("f006", "standard", "fraud",            "disagreement",   0.65),
]

for event_id, tier, category, failure_type, risk_score in FAILURES:
    rca.record_failure(
        event_id=event_id, tier=tier, category=category,
        failure_type=failure_type, risk_score=risk_score,
        signals=SIGNALS,
    )

# ── generate report ────────────────────────────────────────────────────────

generator = ReportGenerator(
    quality_engine=quality,
    rca_engine=rca,
    total_events=10_000,
)

report = generator.generate()
generator.print_summary(report)
path   = generator.save(report)
print(f"Full report: {path}")