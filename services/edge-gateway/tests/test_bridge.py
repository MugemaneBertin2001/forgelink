"""Tests for the edge-gateway OPC-UA → MQTT bridge.

The gateway is the OT-side partner of the MQTT bridge: it reads
OPC-UA data-change notifications and publishes them onto the UNS
MQTT topic tree. These tests pin the two pieces of logic that
actually decide what goes onto the wire:

1. ``_path_to_mqtt_topic`` — CamelCase OPC-UA paths → kebab-case
   UNS topics. If this drifts, the MQTT bridge's UNS regex will
   drop every message into ``dlq.unparseable``.
2. ``datachange_notification`` — dead-band filtering, sequence
   numbers, buffer-on-disconnect. A regression here silently
   loses telemetry or floods the broker.
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from gateway.bridge import BufferedMessage, EdgeGateway


@pytest.fixture
def gateway():
    """Fresh gateway with mocked MQTT client."""
    g = EdgeGateway()
    g.mqtt_client = MagicMock()
    g._mqtt_connected = True
    return g


def _mock_node(node_id: str):
    node = MagicMock()
    node.nodeid.to_string.return_value = node_id
    return node


def _mock_datachange(status_good: bool = True):
    """Build a DataChangeNotif-like object the bridge can read."""
    data = MagicMock()
    data.monitored_item.Value.StatusCode.is_good.return_value = status_good
    data.monitored_item.Value.StatusCode.is_bad.return_value = not status_good
    return data


# ──────────────────────────────────────────────────────────────
# CamelCase OPC-UA path → kebab-case UNS MQTT topic
# ──────────────────────────────────────────────────────────────


class TestPathToMqttTopic:
    """The gateway produces the topic string that the MQTT bridge's
    regex then has to accept. The MQTT bridge regex is permissive
    (``[^/]+`` per level), so these tests pin the **current** output
    exactly — including a known quirk flagged below — rather than
    the format the docstring in ``bridge.py`` suggests.

    KNOWN BUG (pinned here, not fixed): the kebab-case converter
    injects a hyphen before *every* inner uppercase char, so
    ``EAF1`` becomes ``e-a-f1`` rather than ``eaf-1``. Both parse
    through the bridge's regex (it accepts any ``[^/]+``), but the
    device IDs that reach Kafka do **not** round-trip back to the
    canonical Django IDs (``temp-sensor-001``). Fixing this is a
    separate change — these tests lock the current behavior so any
    fix has to update them in lockstep.
    """

    def test_full_isa95_path_current_behavior(self, gateway):
        # Asserts the quirky (current) output — NOT the docstring.
        topic = gateway._path_to_mqtt_topic(
            "SteelPlantKigali/MeltShop/EAF1/ElectrodeA/TempSensor001"
        )
        assert topic == (
            "forgelink/steel-plant-kigali/melt-shop/e-a-f1/"
            "electrode-a/temp-sensor001/telemetry"
        )

    def test_path_always_gets_telemetry_suffix(self, gateway):
        topic = gateway._path_to_mqtt_topic("Plant/Area/Line/Cell/Device")
        assert topic.endswith("/telemetry")

    def test_leading_uppercase_does_not_get_leading_hyphen(self, gateway):
        # "SteelPlantKigali" → "steel-plant-kigali" (no leading '-')
        # because the i>0 guard skips the first char.
        topic = gateway._path_to_mqtt_topic("SteelPlantKigali/A/B/C/D")
        assert topic.split("/")[1] == "steel-plant-kigali"

    def test_shallow_path_still_builds_topic(self, gateway):
        # The gateway maps levels 1-by-1 and appends /telemetry.
        # A shallow OPC-UA path produces a shallow topic — the MQTT
        # bridge will DLQ it, which is the intended loud failure.
        topic = gateway._path_to_mqtt_topic("Plant")
        assert topic == "forgelink/plant/telemetry"


# ──────────────────────────────────────────────────────────────
# OPC-UA status code → quality string
# ──────────────────────────────────────────────────────────────


class TestStatusToQuality:
    def test_good_status(self, gateway):
        sc = MagicMock()
        sc.is_good.return_value = True
        sc.is_bad.return_value = False
        assert gateway._status_to_quality(sc) == "good"

    def test_bad_status(self, gateway):
        sc = MagicMock()
        sc.is_good.return_value = False
        sc.is_bad.return_value = True
        assert gateway._status_to_quality(sc) == "bad"

    def test_uncertain_status(self, gateway):
        # Neither good nor bad → uncertain. OPC-UA defines this as
        # the in-between state (sensor alive but untrusted).
        sc = MagicMock()
        sc.is_good.return_value = False
        sc.is_bad.return_value = False
        assert gateway._status_to_quality(sc) == "uncertain"


# ──────────────────────────────────────────────────────────────
# datachange_notification — the hot path
# ──────────────────────────────────────────────────────────────


class TestDataChangeNotification:
    """Every OPC-UA subscription callback runs through this
    function. These tests pin what goes onto MQTT, what the
    sequence numbers do, and how buffering behaves."""

    @pytest.mark.asyncio
    async def test_publishes_to_mapped_topic(self, gateway):
        node = _mock_node("ns=2;s=dev-1")
        gateway.node_mapping["ns=2;s=dev-1"] = (
            "forgelink/steel-plant-kigali/melt-shop/eaf-1/"
            "electrode-a/temp-sensor-001/telemetry"
        )
        gateway._sequences["ns=2;s=dev-1"] = 0

        await gateway.datachange_notification(node, 1547.3, _mock_datachange())

        gateway.mqtt_client.publish.assert_called_once()
        args = gateway.mqtt_client.publish.call_args
        topic, payload = args[0][0], args[0][1]
        assert topic.endswith("/telemetry")
        msg = json.loads(payload)
        assert msg["value"] == 1547.3
        assert msg["quality"] == "good"
        assert msg["device_id"] == "temp-sensor-001"
        assert msg["sequence"] == 1

    @pytest.mark.asyncio
    async def test_unknown_node_is_silently_dropped(self, gateway):
        # No entry in node_mapping — don't publish anything.
        node = _mock_node("ns=2;s=ghost")
        await gateway.datachange_notification(node, 1.0, _mock_datachange())
        gateway.mqtt_client.publish.assert_not_called()

    @pytest.mark.asyncio
    async def test_sequence_numbers_monotonic_per_node(self, gateway):
        node = _mock_node("ns=2;s=dev-seq")
        gateway.node_mapping["ns=2;s=dev-seq"] = "forgelink/p/a/l/c/d/telemetry"
        gateway._sequences["ns=2;s=dev-seq"] = 0

        for _ in range(3):
            await gateway.datachange_notification(
                node, 42.0 + _, _mock_datachange()
            )

        seqs = [
            json.loads(call.args[1])["sequence"]
            for call in gateway.mqtt_client.publish.call_args_list
        ]
        assert seqs == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_buffers_when_mqtt_disconnected(self, gateway):
        gateway._mqtt_connected = False
        node = _mock_node("ns=2;s=buffered")
        gateway.node_mapping["ns=2;s=buffered"] = "forgelink/p/a/l/c/d/telemetry"
        gateway._sequences["ns=2;s=buffered"] = 0

        await gateway.datachange_notification(node, 99.9, _mock_datachange())

        gateway.mqtt_client.publish.assert_not_called()
        assert len(gateway.buffer) == 1
        assert isinstance(gateway.buffer[0], BufferedMessage)
        assert gateway.buffer[0].topic.endswith("/telemetry")

    @pytest.mark.asyncio
    async def test_none_value_treated_as_zero(self, gateway):
        # Defensive: a None value from OPC-UA shouldn't crash the loop.
        node = _mock_node("ns=2;s=nullable")
        gateway.node_mapping["ns=2;s=nullable"] = "forgelink/p/a/l/c/d/telemetry"
        gateway._sequences["ns=2;s=nullable"] = 0

        await gateway.datachange_notification(node, None, _mock_datachange())

        payload = json.loads(gateway.mqtt_client.publish.call_args.args[1])
        assert payload["value"] == 0.0


# ──────────────────────────────────────────────────────────────
# Dead-band filtering — suppress tiny fluctuations
# ──────────────────────────────────────────────────────────────


class TestDeadBandFiltering:
    """When configured with a non-zero dead_band, the gateway
    must suppress deltas below the threshold (reduces traffic
    across the OT↔IT boundary)."""

    @pytest.mark.asyncio
    async def test_small_delta_suppressed_when_deadband_active(
        self, gateway, monkeypatch
    ):
        from gateway import bridge as bridge_mod

        monkeypatch.setattr(bridge_mod.settings, "dead_band", 1.0)

        node = _mock_node("ns=2;s=deadband")
        gateway.node_mapping["ns=2;s=deadband"] = "forgelink/p/a/l/c/d/telemetry"
        gateway._sequences["ns=2;s=deadband"] = 0

        # First call seeds the last-value cache (always publishes).
        await gateway.datachange_notification(node, 100.0, _mock_datachange())
        # Delta of 0.5 < 1.0 — must NOT publish again.
        await gateway.datachange_notification(node, 100.5, _mock_datachange())

        assert gateway.mqtt_client.publish.call_count == 1

    @pytest.mark.asyncio
    async def test_delta_above_deadband_publishes(self, gateway, monkeypatch):
        from gateway import bridge as bridge_mod

        monkeypatch.setattr(bridge_mod.settings, "dead_band", 1.0)

        node = _mock_node("ns=2;s=deadband-pass")
        gateway.node_mapping["ns=2;s=deadband-pass"] = "forgelink/p/a/l/c/d/telemetry"
        gateway._sequences["ns=2;s=deadband-pass"] = 0

        await gateway.datachange_notification(node, 100.0, _mock_datachange())
        await gateway.datachange_notification(node, 102.0, _mock_datachange())

        assert gateway.mqtt_client.publish.call_count == 2

    @pytest.mark.asyncio
    async def test_zero_deadband_publishes_every_sample(
        self, gateway, monkeypatch
    ):
        # Default config — dead_band=0 means every sample goes out.
        from gateway import bridge as bridge_mod

        monkeypatch.setattr(bridge_mod.settings, "dead_band", 0.0)

        node = _mock_node("ns=2;s=nodead")
        gateway.node_mapping["ns=2;s=nodead"] = "forgelink/p/a/l/c/d/telemetry"
        gateway._sequences["ns=2;s=nodead"] = 0

        for v in (10.0, 10.0, 10.0001):
            await gateway.datachange_notification(node, v, _mock_datachange())

        assert gateway.mqtt_client.publish.call_count == 3


# ──────────────────────────────────────────────────────────────
# Buffer flush on reconnect
# ──────────────────────────────────────────────────────────────


class TestBufferFlush:
    @pytest.mark.asyncio
    async def test_flush_buffer_drains_queue(self, gateway):
        gateway.buffer.append(
            BufferedMessage(topic="t1", payload="p1", timestamp=None)
        )
        gateway.buffer.append(
            BufferedMessage(topic="t2", payload="p2", timestamp=None)
        )

        await gateway._flush_buffer()

        assert len(gateway.buffer) == 0
        assert gateway.mqtt_client.publish.call_count == 2
        topics = [c.args[0] for c in gateway.mqtt_client.publish.call_args_list]
        assert topics == ["t1", "t2"]

    @pytest.mark.asyncio
    async def test_flush_stops_if_mqtt_disconnects_midway(self, gateway):
        gateway.buffer.append(
            BufferedMessage(topic="t1", payload="p1", timestamp=None)
        )
        gateway.buffer.append(
            BufferedMessage(topic="t2", payload="p2", timestamp=None)
        )

        # Flip the connection flag on the first publish; the while
        # loop re-checks _mqtt_connected before pulling the next msg.
        def flip_on_publish(*_args, **_kwargs):
            gateway._mqtt_connected = False

        gateway.mqtt_client.publish.side_effect = flip_on_publish

        await gateway._flush_buffer()

        # First message published, then connection dropped → second
        # message stays in the buffer for a future flush.
        assert gateway.mqtt_client.publish.call_count == 1
        assert len(gateway.buffer) == 1


# ──────────────────────────────────────────────────────────────
# Error containment — one bad notification must not kill the loop
# ──────────────────────────────────────────────────────────────


class TestErrorContainment:
    @pytest.mark.asyncio
    async def test_exception_in_publish_is_swallowed(self, gateway):
        node = _mock_node("ns=2;s=angry")
        gateway.node_mapping["ns=2;s=angry"] = "forgelink/p/a/l/c/d/telemetry"
        gateway._sequences["ns=2;s=angry"] = 0
        gateway.mqtt_client.publish.side_effect = Exception("broker angry")

        # Must not raise — the asyncua subscription loop would die
        # and stop delivering data-change notifications altogether.
        await gateway.datachange_notification(node, 1.0, _mock_datachange())
