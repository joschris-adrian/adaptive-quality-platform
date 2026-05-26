import json
import asyncio
import logging
from kafka import KafkaConsumer, KafkaProducer
from services.detection.pipeline import DetectionPipeline

logger = logging.getLogger(__name__)

class DetectionConsumer:
    def __init__(self):
        self.pipeline = DetectionPipeline()
        self.consumer = KafkaConsumer(
            "raw-events",
            bootstrap_servers=["kafka:9092"],
            group_id="detection-service",
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
        logger.info("Detection consumer started")
        for message in self.consumer:
            event = message.value
            try:
                result = asyncio.run(self.pipeline.run(event))
                self.producer.send(
                    "scored-events",
                    key=event["event_id"].encode(),
                    value=result,
                )
                self.consumer.commit()
                logger.info(
                    f"[{event['event_id']}] score={result['risk_probability']} "
                    f"category={result['category']}"
                )
            except Exception as e:
                logger.error(f"Detection failed for {event.get('event_id')}: {e}")
                self._send_to_dlq(event)

    def _send_to_dlq(self, event: dict):
        self.producer.send("dlq-events", value=event)


if __name__ == "__main__":
    DetectionConsumer().run()