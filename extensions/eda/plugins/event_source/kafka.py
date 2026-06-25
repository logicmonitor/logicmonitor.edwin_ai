"""Consume Edwin AI events from Apache Kafka.

For high-volume enterprise deployments where Edwin AI publishes
alert events to a Kafka topic. The EDA controller consumes from
the configured topic and emits normalized events.

Arguments:
    topic: Kafka topic to consume from (default: 'edwin-ai-alerts')
    bootstrap_servers: Kafka bootstrap servers (default: 'localhost:9092')
    group_id: Consumer group ID (default: 'eda-edwin-ai')
    security_protocol: Kafka security protocol (default: 'PLAINTEXT')
    sasl_mechanism: SASL mechanism if using SASL auth
    sasl_username: SASL username
    sasl_password: SASL password
    ssl_cafile: Path to CA certificate file
"""

import asyncio
import json
import logging
from typing import Any

IMPORT_ERRORS = []
try:
    from aiokafka import AIOKafkaConsumer
except ImportError as ie:
    IMPORT_ERRORS.append(ie)

logger = logging.getLogger(__name__)


async def main(queue: asyncio.Queue, args: dict[str, Any]) -> None:
    """Consume Edwin AI events from Kafka and forward to the EDA rulebook."""
    for exc in IMPORT_ERRORS:
        raise ImportError(
            "The 'aiokafka' package is required for the Kafka event source. "
            "Install it with: pip install aiokafka"
        ) from exc

    topic = args.get("topic", "edwin-ai-alerts")
    bootstrap_servers = args.get("bootstrap_servers", "localhost:9092")
    group_id = args.get("group_id", "eda-edwin-ai")

    consumer_kwargs: dict[str, Any] = {
        "bootstrap_servers": bootstrap_servers,
        "group_id": group_id,
        "auto_offset_reset": "latest",
        "enable_auto_commit": True,
        "value_deserializer": lambda m: json.loads(m.decode("utf-8")),
    }

    security_protocol = args.get("security_protocol", "PLAINTEXT")
    consumer_kwargs["security_protocol"] = security_protocol

    if args.get("sasl_mechanism"):
        consumer_kwargs["sasl_mechanism"] = args["sasl_mechanism"]
        consumer_kwargs["sasl_plain_username"] = args.get(
            "sasl_username", ""
        )
        consumer_kwargs["sasl_plain_password"] = args.get(
            "sasl_password", ""
        )

    if args.get("ssl_cafile"):
        consumer_kwargs["ssl_cafile"] = args["ssl_cafile"]

    consumer = AIOKafkaConsumer(topic, **consumer_kwargs)

    await consumer.start()
    logger.info(
        "Edwin AI Kafka consumer started on topic '%s' at %s",
        topic,
        bootstrap_servers,
    )

    try:
        async for message in consumer:
            try:
                data = message.value
                if isinstance(data, str):
                    data = json.loads(data)
                if not isinstance(data, dict):
                    logger.warning("Skipping non-dict Kafka message")
                    continue
                event = _normalize_event(data)
                await queue.put(event)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Skipping malformed Kafka message")
    finally:
        await consumer.stop()


def _normalize_event(data: dict) -> dict:
    return {
        "edwin_ai": {
            "event_type": data.get("type", data.get("eventType", "alert")),
            "alert_id": str(data.get("alertId", data.get("id", ""))),
            "severity": data.get(
                "severity", data.get("level", "unknown")
            ),
            "host": data.get(
                "host",
                data.get("resourceName", data.get("device", "")),
            ),
            "message": data.get(
                "message",
                data.get("description", data.get("summary", "")),
            ),
            "metric": data.get("metric", data.get("datapoint", "")),
            "value": data.get("value", data.get("currentValue", "")),
            "threshold": data.get("threshold", ""),
            "resource_group": data.get(
                "resourceGroup", data.get("group", "")
            ),
            "timestamp": data.get(
                "timestamp", data.get("startEpoch", "")
            ),
            "status": data.get(
                "status", data.get("alertStatus", "active")
            ),
            "raw": data,
        }
    }
