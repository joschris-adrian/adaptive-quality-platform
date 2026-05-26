import json
import logging
from kafka import KafkaConsumer, KafkaProducer
from services.routing.engine import RoutingEngine

logger = logging.getLogger(__name__)


class RoutingConsumer:
    def __init__(self):
        self.engine   = RoutingEngine()
        self.consumer = KafkaConsumer(
            "review-queue",
            bootstrap_servers=["kafka:9092"],
            group_id="routing-service",
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
        logger.info("Routing consumer started")
        for message in self.consumer:
            event = message.value
            try:
                routed = self.engine.route(event)
                self.producer.send(
                    routed["queue"],
                    key=routed["event_id"].encode(),
                    value=routed,
                )
                self.engine.capacity.increment(routed["tier"])
                self.consumer.commit()
                logger.info(
                    f"[{routed['event_id']}] "
                    f"action={routed['action']} "
                    f"tier={routed['tier']} "
                    f"queue={routed['queue']} "
                    f"sla={routed['sla_minutes']}min"
                )
            except Exception as e:
                logger.error(f"Routing failed: {e}")
                self.producer.send("dlq-events", value=event)


if __name__ == "__main__":
    RoutingConsumer().run()