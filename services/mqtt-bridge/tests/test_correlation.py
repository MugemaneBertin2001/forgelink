"""Tests for correlation-ID propagation into outgoing Kafka headers.

The bridge is the OT→IT boundary: every MQTT telemetry message
should carry an ``x-correlation-id`` onto Kafka so the Django
telemetry consumer can continue the trace. These tests pin:

1. The bridge binds a fresh correlation ID per _on_message.
2. Both the happy path and the DLQ path include the header.
3. A successful message + an unparseable one each get their own
   ID (no leakage across messages).
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from bridge.correlation import KAFKA_HEADER
from bridge.mqtt_client import MQTTBridge


@pytest.fixture
def bridge():
    b = MQTTBridge()
    b.kafka_producer = MagicMock()
    return b


def _valid_payload() -> bytes:
    return json.dumps(
        {
            "device_id": "temp-sensor-001",
            "value": 1547.3,
            "quality": "good",
            "timestamp": "2026-04-23T10:00:00Z",
        }
    ).encode()


def _header_value(call_kwargs) -> str | None:
    for key, value in call_kwargs.get("headers") or []:
        if key == KAFKA_HEADER:
            return value.decode()
    return None


class TestCorrelationIdPropagation:
    def test_happy_path_attaches_header(self, bridge):
        topic = (
            "forgelink/steel-plant-kigali/melt-shop/eaf-1/"
            "electrode-a/temp-sensor-001/telemetry"
        )
        msg = MagicMock(topic=topic, payload=_valid_payload())
        bridge._on_message(None, None, msg)

        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        assert _header_value(kwargs) is not None
        # UUID4 shape sanity check (36 chars, hyphens at expected positions).
        id_value = _header_value(kwargs)
        assert len(id_value) == 36 and id_value.count("-") == 4

    def test_dlq_path_attaches_header(self, bridge):
        # Invalid topic → DLQ. Header must still be present so the
        # ingest team can trace a bad upstream device back to a
        # specific MQTT message.
        msg = MagicMock(topic="garbage", payload=b"whatever")
        bridge._on_message(None, None, msg)

        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        assert kwargs["topic"] == "dlq.unparseable"
        assert _header_value(kwargs) is not None

    def test_two_messages_get_different_ids(self, bridge):
        topic = (
            "forgelink/steel-plant-kigali/melt-shop/eaf-1/"
            "electrode-a/temp-sensor-001/telemetry"
        )

        bridge._on_message(None, None, MagicMock(topic=topic, payload=_valid_payload()))
        first_id = _header_value(
            bridge.kafka_producer.produce.call_args.kwargs
        )

        bridge._on_message(None, None, MagicMock(topic=topic, payload=_valid_payload()))
        second_id = _header_value(
            bridge.kafka_producer.produce.call_args.kwargs
        )

        assert first_id and second_id and first_id != second_id

    def test_context_cleared_between_messages(self, bridge):
        """A correlation ID must not leak from one _on_message to the next.

        After _on_message returns, get_correlation() should be None —
        otherwise a later unrelated log line would pick up a stale ID.
        """
        from bridge.correlation import get

        topic = (
            "forgelink/steel-plant-kigali/melt-shop/eaf-1/"
            "electrode-a/temp-sensor-001/telemetry"
        )
        bridge._on_message(None, None, MagicMock(topic=topic, payload=_valid_payload()))
        assert get() is None
