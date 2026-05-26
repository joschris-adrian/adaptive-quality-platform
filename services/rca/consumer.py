import json
import logging
from kafka import KafkaConsumer
from services.rca.root_cause import RCAEngine

logger = logging.getLogger(__name__)


class RCAConsumer:
    """
    Subscribes to review-outcomes and reversals topics.
    Builds failure records from labelled decisions and reversals.
    """

    def __init__(self, engine: RCAEngine = None):
        self.engine = engine or RCAEngine()

        self.outcome_consumer = KafkaConsumer(
            "review-outcomes",
            bootstrap_servers=["kafka:9092"],
            group_id="rca-outcomes",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

    def process_outcome(self, event: dict):
        predicted    = event.get("predicted")
        ground_truth = event.get("ground_truth")

        if not predicted or not ground_truth:
            return

        failure_type = None
        if predicted == "positive" and ground_truth == "negative":
            failure_type = "false_positive"
        elif predicted == "negative" and ground_truth == "positive":
            failure_type = "false_negative"
        elif event.get("reversed"):
            failure_type = "reversal"
        elif event.get("disagreement"):
            failure_type = "disagreement"

        if failure_type:
            self.engine.record_failure(
                event_id=     event["event_id"],
                tier=         event["tier"],
                category=     event["category"],
                failure_type= failure_type,
                risk_score=   event.get("risk_score", 0.0),
                signals=      event.get("signals", {}),
                reviewer_id=  event.get("reviewer_id"),
                metadata=     event.get("metadata", {}),
            )

    def run(self):
        logger.info("RCA consumer started")
        for message in self.outcome_consumer:
            try:
                self.process_outcome(message.value)
                self.outcome_consumer.commit()
            except Exception as e:
                logger.error(f"RCA processing error: {e}")


if __name__ == "__main__":
    RCAConsumer().run()