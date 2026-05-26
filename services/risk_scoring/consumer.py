import json
import logging
from kafka import KafkaConsumer, KafkaProducer
from services.risk_scoring.scorer import RiskScorer

logger = logging.getLogger(__name__)


class RiskScoringConsumer:
    def __init__(self):
        self.scorer   = RiskScorer()
        self.consumer = KafkaConsumer(
            "scored-events",
            bootstrap_servers=["kafka:9092"],
            group_id="risk-scoring-service",
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        self.producer = KafkaProducer(
            bootstrap_servers=["kafka:9092"],
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            acks="all",
        )

    def run(self):
        logger.info("Risk scoring consumer started")
        for message in self.consumer:
            event = message.value
            try:
                risk_result = self.scorer.score(event)
                self._route(risk_result)
                self.consumer.commit()
                logger.info(
                    f"[{risk_result['event_id']}] "
                    f"score={risk_result['risk_score']} "
                    f"priority={risk_result['priority']}"
                )
            except Exception as e:
                logger.error(f"Risk scoring failed: {e}")
                self.producer.send("dlq-events", value=event)

    def _route(self, risk_result: dict):
        priority = risk_result["priority"]
        topic_map = {
            "critical": "review-queue",
            "high":     "review-queue",
            "medium":   "review-queue",
            "low":      "auto-actioned-events",   # no human review needed
        }
        topic = topic_map[priority]
        self.producer.send(
            topic,
            key=risk_result["event_id"].encode(),
            value=risk_result,
        )


if __name__ == "__main__":
    RiskScoringConsumer().run()