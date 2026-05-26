import psycopg2
import logging
import time
import os
from services.analytics.metrics import QualityAnalyticsEngine

logger  = logging.getLogger(__name__)
DB_URL  = os.getenv("DATABASE_URL", "postgresql://aqp:aqp_secret@localhost:5432/adaptive_quality")
INTERVAL = int(os.getenv("SNAPSHOT_INTERVAL_SECONDS", "900"))   # 15 min


def write_snapshot(engine: QualityAnalyticsEngine):
    snap = engine.snapshot()
    gm   = snap["global_metrics"]
    esc  = snap["escalation"]
    rev  = snap["reversal"]

    conn = psycopg2.connect(DB_URL)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO quality_snapshots (
                    total_decisions, labelled_count,
                    precision, recall, f1,
                    false_positive_rate, false_negative_rate,
                    escalation_rate, reversal_rate
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """, (
                snap["total_decisions"],
                snap["labelled_count"],
                gm["precision"],
                gm["recall"],
                gm["f1"],
                gm["false_positive_rate"],
                gm["false_negative_rate"],
                esc["escalation_rate"],
                rev["reversal_rate"],
            ))
        conn.commit()
        logger.info(f"Snapshot written — precision={gm['precision']} recall={gm['recall']}")
    finally:
        conn.close()


def run(engine: QualityAnalyticsEngine):
    logger.info(f"Snapshot writer started — interval={INTERVAL}s")
    while True:
        try:
            write_snapshot(engine)
        except Exception as e:
            logger.error(f"Snapshot write failed: {e}")
        time.sleep(INTERVAL)