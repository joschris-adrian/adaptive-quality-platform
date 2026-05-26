import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.risk_scoring.scorer import RiskScorer

scorer = RiskScorer()

test_cases = [
    {
        "event_id": "test-001",
        "risk_probability": 0.92,
        "category": "fraud",
        "signals": {
            "ml":        {"risk_probability": 0.91, "category": "fraud"},
            "rule":      {"risk_probability": 1.00, "category": "fraud", "rules_triggered": ["blocklisted_user"]},
            "heuristic": {"risk_probability": 0.60, "category": "spam", "signals": {"spam_patterns": 0.7}},
        },
        "source_event": {"event_type": "transaction", "source_system": "api"},
    },
    {
        "event_id": "test-002",
        "risk_probability": 0.35,
        "category": "clean",
        "signals": {
            "ml":        {"risk_probability": 0.35, "category": "clean"},
            "rule":      {"risk_probability": 0.00, "category": "clean", "rules_triggered": []},
            "heuristic": {"risk_probability": 0.10, "category": "clean", "signals": {}},
        },
        "source_event": {"event_type": "user_action", "source_system": "web"},
    },
]

for tc in test_cases:
    result = scorer.score(tc)
    print(
        f"[{result['event_id']}] "
        f"score={result['risk_score']} "
        f"priority={result['priority']} "
        f"components={result['components']}"
    )