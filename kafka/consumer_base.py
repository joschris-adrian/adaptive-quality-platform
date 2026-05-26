from kafka import KafkaConsumer
from kafka.errors import KafkaError
import json, logging

logger = logging.getLogger(__name__)

class BaseConsumer:
    def __init__(self, topic: str, group_id: str):
        self.consumer = KafkaConsumer(
            topic,
            bootstrap_servers=["kafka:9092"],
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )

    def run(self):
        for message in self.consumer:
            try:
                self.process(message.value)
                self.consumer.commit()
            except Exception as e:
                logger.error(f"Processing failed: {e} — routing to DLQ")
                self._send_to_dlq(message.value)

    def process(self, event: dict):
        raise NotImplementedError

    def _send_to_dlq(self, event: dict):
        # publish to dlq-events topic via a shared producer
        pass