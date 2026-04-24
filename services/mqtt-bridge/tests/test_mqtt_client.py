"""Tests for the MQTT → Kafka bridge.

The bridge is the OT↔IT boundary: every message from the plant
floor passes through ``_process_message``. These tests pin the
parsing + routing contract so a regression here (bad topic
grammar, wrong Kafka topic for an area, silently-dropped DLQ
path) fails loud in CI instead of silently on the production demo.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock

import pytest

from bridge.mqtt_client import MQTTBridge


@pytest.fixture
def bridge():
    """Fresh bridge with a mocked Kafka producer."""
    b = MQTTBridge()
    b.kafka_producer = MagicMock()
    return b


def _valid_payload(**overrides):
    payload = {
        "device_id": "temp-sensor-001",
        "value": 1547.3,
        "quality": "good",
        "timestamp": "2026-04-23T10:00:00Z",
    }
    payload.update(overrides)
    return json.dumps(payload).encode("utf-8")


# ──────────────────────────────────────────────────────────────
# UNS topic parsing
# ──────────────────────────────────────────────────────────────


class TestUnsTopicParsing:
    """The regex in MQTTBridge.UNS_PATTERN pins the topic grammar.

    Every change to uns-topic-hierarchy.md MUST come with a change
    here (or a test case) so the two stay in sync.
    """

    def test_valid_telemetry_topic_matches(self, bridge):
        topic = "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry"
        bridge._process_message(topic, _valid_payload())
        bridge.kafka_producer.produce.assert_called_once()
        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        assert kwargs["topic"] == "telemetry.melt-shop"
        # Enriched payload carries every hierarchy level.
        published = json.loads(kwargs["value"])
        assert published["_plant"] == "steel-plant-kigali"
        assert published["_area"] == "melt-shop"
        assert published["_line"] == "eaf-1"
        assert published["_cell"] == "electrode-a"
        assert published["_topic"] == topic

    def test_valid_topic_with_status_type(self, bridge):
        topic = "forgelink/steel-plant-kigali/finishing/bundling/station-1/weight-001/status"
        bridge._process_message(topic, _valid_payload())
        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        assert kwargs["topic"] == "status.all"

    def test_valid_topic_with_events_type(self, bridge):
        topic = "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/events"
        bridge._process_message(topic, _valid_payload())
        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        assert kwargs["topic"] == "events.all"

    def test_valid_topic_with_commands_type(self, bridge):
        topic = "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/commands"
        bridge._process_message(topic, _valid_payload())
        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        assert kwargs["topic"] == "commands.all"

    @pytest.mark.parametrize(
        "bad_topic",
        [
            "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a",           # too shallow
            "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/t001/t/x",  # too deep
            "different-root/steel-plant-kigali/melt-shop/eaf-1/electrode-a/t001/telemetry",
            "forgelink//melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry",   # empty plant
            "forgelink/p/a/l/c/d/weird-type",                                     # invalid type
            "",
        ],
    )
    def test_invalid_topics_routed_to_dlq(self, bridge, bad_topic):
        bridge._process_message(bad_topic, b"{}")
        bridge.kafka_producer.produce.assert_called_once()
        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        assert kwargs["topic"] == "dlq.unparseable"


# ──────────────────────────────────────────────────────────────
# Per-area Kafka topic routing
# ──────────────────────────────────────────────────────────────


class TestKafkaTopicRouting:
    @pytest.mark.parametrize(
        "area,expected_topic",
        [
            ("melt-shop", "telemetry.melt-shop"),
            ("continuous-casting", "telemetry.continuous-casting"),
            ("rolling-mill", "telemetry.rolling-mill"),
            ("finishing", "telemetry.finishing"),
        ],
    )
    def test_known_areas_route_to_dedicated_topic(self, bridge, area, expected_topic):
        assert bridge._get_kafka_topic("telemetry", area) == expected_topic

    def test_unknown_area_falls_back_to_prefixed_topic(self, bridge):
        # Lets new areas flow through without a code change — the
        # downstream Django consumer is responsible for ignoring
        # non-declared topics gracefully (auto-created).
        assert bridge._get_kafka_topic("telemetry", "new-area") == "telemetry.new-area"

    def test_events_go_to_single_topic(self, bridge):
        assert bridge._get_kafka_topic("events", "melt-shop") == "events.all"

    def test_status_goes_to_single_topic(self, bridge):
        assert bridge._get_kafka_topic("status", "rolling-mill") == "status.all"

    def test_commands_goes_to_single_topic(self, bridge):
        assert bridge._get_kafka_topic("commands", "finishing") == "commands.all"

    def test_unknown_message_type_routes_to_dlq(self, bridge):
        # The regex rejects invalid types before this function ever
        # sees them, but belt + braces: an unexpected msg_type does
        # NOT leak into an arbitrary topic.
        assert bridge._get_kafka_topic("bogus", "melt-shop") == "dlq.unparseable"


# ──────────────────────────────────────────────────────────────
# Payload parsing and DLQ routing
# ──────────────────────────────────────────────────────────────


class TestPayloadHandling:
    def test_invalid_json_payload_routed_to_dlq(self, bridge):
        topic = "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry"
        bridge._process_message(topic, b"this is not json")
        bridge.kafka_producer.produce.assert_called_once()
        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        assert kwargs["topic"] == "dlq.unparseable"
        # DLQ message carries original topic + raw payload for forensic.
        dlq_payload = json.loads(kwargs["value"])
        assert dlq_payload["original_topic"] == topic
        assert "this is not json" in dlq_payload["payload"]

    def test_payload_enriched_with_device_id_as_key(self, bridge):
        topic = "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry"
        bridge._process_message(topic, _valid_payload())
        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        # Kafka key = device_id so per-device ordering within a partition holds.
        assert kwargs["key"] == b"temp-sensor-001"

    def test_empty_payload_still_enriched(self, bridge):
        # `{}` is valid JSON — the bridge should enrich with topic
        # metadata even if the producer sent nothing in the body.
        topic = "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry"
        bridge._process_message(topic, b"{}")
        kwargs = bridge.kafka_producer.produce.call_args.kwargs
        published = json.loads(kwargs["value"])
        assert published["_area"] == "melt-shop"
        assert published["_plant"] == "steel-plant-kigali"


# ──────────────────────────────────────────────────────────────
# Error containment at the MQTT callback boundary
# ──────────────────────────────────────────────────────────────


class TestMqttCallbackContainment:
    """_on_message wraps _process_message so a single bad message
    never kills the bridge. A regression here would mean one
    poisonous payload takes the entire OT↔IT boundary offline."""

    def test_on_message_swallows_exceptions(self, bridge):
        # Simulate a paho Message object where payload raises on decode.
        broken_msg = MagicMock()
        broken_msg.topic = "forgelink/p/a/l/c/d/telemetry"
        broken_msg.payload = MagicMock()
        broken_msg.payload.decode.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "broken")

        # Must not raise.
        bridge._on_message(None, None, broken_msg)

    def test_kafka_producer_failure_does_not_crash(self, bridge):
        topic = "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry"
        bridge.kafka_producer.produce.side_effect = Exception("kafka is down")

        # Must not raise — the bridge process should keep consuming MQTT
        # even if downstream Kafka is transiently broken. The Prometheus
        # error counter (asserted separately) is what alerts on this.
        bridge._process_message(topic, _valid_payload())
