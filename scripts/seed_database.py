import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
import random
import uuid
from datetime import datetime, timezone, timedelta

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://aqp:aqp_secret@localhost:5432/adaptive_quality"
)

TIERS       = ["automated", "standard", "expert"]
CATEGORIES  = ["fraud", "policy_violation", "spam", "abuse", "clean"]
PREDICTED   = ["positive", "negative"]
REVIEWER_GROUPS = ["standard", "expert"]


def random_ts(days_ago_max=30):
    offset = random.uniform(0, days_ago_max * 24 * 3600)
    return datetime.now(timezone.utc) - timedelta(seconds=offset)


def seed_decisions(cur, n=500):
    print(f"Seeding {n} decisions...")
    for _ in range(n):
        tier         = random.choice(TIERS)
        category     = random.choice(CATEGORIES)
        predicted    = random.choice(PREDICTED)
        ground_truth = random.choice(PREDICTED + [None, None])
        risk_score   = round(random.uniform(0.0, 1.0), 4)
        escalated    = tier in ("standard", "expert")
        reversed_    = random.random() < 0.05
        created_at   = random_ts(30)
        reviewed_at  = (
            created_at + timedelta(minutes=random.uniform(1, 120))
            if ground_truth else None
        )

        cur.execute("""
            INSERT INTO decisions (
                event_id, tier, category, predicted, ground_truth,
                risk_score, escalated, reversed, created_at, reviewed_at
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            ON CONFLICT (event_id) DO NOTHING
        """, (
            str(uuid.uuid4()), tier, category, predicted, ground_truth,
            risk_score, escalated, reversed_, created_at, reviewed_at,
        ))


def seed_reviews(cur, n=200):
    print(f"Seeding {n} reviews...")
    for _ in range(n):
        # fetch a random event_id from decisions
        cur.execute("SELECT event_id FROM decisions ORDER BY RANDOM() LIMIT 1")
        row = cur.fetchone()
        if not row:
            continue
        event_id       = row[0]
        reviewer_id    = f"reviewer-{random.randint(1, 10):02d}"
        reviewer_group = random.choice(REVIEWER_GROUPS)
        decision       = random.choice(PREDICTED)
        agreement      = round(random.uniform(0.5, 1.0), 3)

        cur.execute("""
            INSERT INTO reviews (
                event_id, reviewer_id, reviewer_group,
                decision, agreement_score
            ) VALUES (%s,%s,%s,%s,%s)
        """, (event_id, reviewer_id, reviewer_group, decision, agreement))


def seed_quality_snapshots(cur, n=50):
    print(f"Seeding {n} quality snapshots...")
    for i in range(n):
        snapshot_at  = datetime.now(timezone.utc) - timedelta(minutes=15 * (n - i))
        precision    = round(random.uniform(0.75, 0.95), 4)
        recall       = round(random.uniform(0.70, 0.92), 4)
        f1           = round(2 * precision * recall / (precision + recall), 4)
        fpr          = round(random.uniform(0.02, 0.15), 4)
        fnr          = round(random.uniform(0.05, 0.20), 4)
        esc_rate     = round(random.uniform(0.10, 0.40), 4)
        rev_rate     = round(random.uniform(0.01, 0.10), 4)
        total        = random.randint(800, 1200)
        labelled     = int(total * random.uniform(0.6, 0.9))

        cur.execute("""
            INSERT INTO quality_snapshots (
                snapshot_at, total_decisions, labelled_count,
                precision, recall, f1,
                false_positive_rate, false_negative_rate,
                escalation_rate, reversal_rate
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            snapshot_at, total, labelled,
            precision, recall, f1,
            fpr, fnr, esc_rate, rev_rate,
        ))


def seed_rca_failures(cur, n=100):
    print(f"Seeding {n} RCA failures...")
    failure_types = ["false_positive", "false_negative", "reversal", "disagreement"]
    import json
    for _ in range(n):
        cur.execute("""
            INSERT INTO rca_failures (
                event_id, tier, category, failure_type,
                risk_score, signals, reviewer_id
            ) VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (
            str(uuid.uuid4()),
            random.choice(TIERS),
            random.choice(CATEGORIES),
            random.choice(failure_types),
            round(random.uniform(0.3, 0.95), 4),
            json.dumps({
                "ml":        {"risk_probability": round(random.uniform(0.3, 0.95), 4)},
                "rule":      {"risk_probability": round(random.uniform(0.0, 0.8),  4)},
                "heuristic": {"signals": {"spam_patterns": round(random.random(), 4)}},
            }),
            f"reviewer-{random.randint(1, 10):02d}" if random.random() > 0.5 else None,
        ))


def main():
    print(f"Connecting to {DATABASE_URL}...")
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            seed_decisions(cur, n=500)
            seed_reviews(cur, n=200)
            seed_quality_snapshots(cur, n=50)
            seed_rca_failures(cur, n=100)
        conn.commit()
        print("\nDatabase seeded successfully.")
        print("Refresh Grafana dashboards at http://localhost:3000")
    finally:
        conn.close()


if __name__ == "__main__":
    main()