import json
import logging
from kafka import KafkaConsumer
from services.analytics.metrics import QualityAnalyticsEngine

logger = logging.getLogger(__name__)


class AnalyticsConsumer:
    """
    Listens to three topics:
      - routed-decisions  : new decisions as they are routed
      - review-outcomes   : ground truth labels from human reviewers
      - reversals         : events where a decision was overturned
    """

    def __init__(self, engine: QualityAnalyticsEngine = None):
        self.engine = engine or QualityAnalyticsEngine()

        self.decision_consumer = KafkaConsumer(
            "routed-decisions",
            bootstrap_servers=["kafka:9092"],
            group_id="analytics-decisions",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        self.outcome_consumer = KafkaConsumer(
            "review-outcomes",
            bootstrap_servers=["kafka:9092"],
            group_id="analytics-outcomes",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

    def process_decision(self, event: dict):
        self.engine.record_decision(
            event_id=    event["event_id"],
            tier=        event["tier"],
            category=    event["category"],
            predicted=   "positive" if event["risk_score"] >= 0.5 else "negative",
            risk_score=  event["risk_score"],
            reviewer_id= event.get("reviewer_id"),
            escalated=   event.get("action") in ("escalated_review", "hold"),
        )

    def process_outcome(self, event: dict):
        ground_truth = event.get("ground_truth")
        event_id     = event.get("event_id")
        reversed_    = event.get("reversed", False)

        if ground_truth:
            try:
                self.engine.record_ground_truth(event_id, ground_truth)
            except KeyError:
                logger.warning(f"Outcome for unknown event {event_id}")

        if reversed_:
            self.engine.record_reversal(event_id)

    def run_decisions(self):
        for message in self.decision_consumer:
            try:
                self.process_decision(message.value)
                self.decision_consumer.commit()
            except Exception as e:
                logger.error(f"Decision processing error: {e}")

    def run_outcomes(self):
        for message in self.outcome_consumer:
            try:
                self.process_outcome(message.value)
                self.outcome_consumer.commit()
            except Exception as e:
                logger.error(f"Outcome processing error: {e}")