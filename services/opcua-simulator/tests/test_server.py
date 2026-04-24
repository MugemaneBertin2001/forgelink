"""Tests for the OPC-UA simulation server.

The server is the source of truth for the virtual plant: Django
pushes value updates to Redis, this server writes them into its
OPC-UA address space, and the edge-gateway reads them back out.
These tests pin the two contract-bearing bits of logic:

1. ``_quality_to_status`` — quality string → OPC-UA StatusCode.
   The edge-gateway reads the status back and turns it into the
   quality string published on MQTT. A regression here means an
   alert rule keyed on quality could misfire.
2. ``handle_value_update`` — JSON-from-Redis → node write. This
   is the whole reason the process exists; a bad parse silently
   stops updates for one device.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from asyncua import ua

from simulator.server import OPCUASimulator


@pytest.fixture
def sim():
    return OPCUASimulator()


# ──────────────────────────────────────────────────────────────
# Quality string → OPC-UA StatusCode
# ──────────────────────────────────────────────────────────────


class TestQualityToStatus:
    """The edge-gateway's inverse translation is tested separately;
    these two must stay symmetric or quality info round-trips wrong.
    """

    def test_good(self, sim):
        status = sim._quality_to_status("good")
        assert isinstance(status, ua.StatusCode)
        assert status.is_good()

    def test_bad(self, sim):
        status = sim._quality_to_status("bad")
        assert status.is_bad()

    def test_uncertain(self, sim):
        # Anything that isn't "good" or "bad" becomes Uncertain —
        # defensive default so a malformed payload doesn't get
        # accidentally promoted to "good".
        status = sim._quality_to_status("uncertain")
        assert not status.is_good()
        assert not status.is_bad()

    def test_unknown_string_maps_to_uncertain(self, sim):
        status = sim._quality_to_status("garbage")
        assert not status.is_good()
        assert not status.is_bad()


# ──────────────────────────────────────────────────────────────
# handle_value_update — the Redis → OPC-UA write path
# ──────────────────────────────────────────────────────────────


class TestHandleValueUpdate:
    @pytest.mark.asyncio
    async def test_unknown_node_silently_skipped(self, sim):
        # Must not raise: Django may push updates for a device that
        # was removed after the server built its address space.
        await sim.handle_value_update(
            {"opc_node_id": "ns=2;s=ghost", "value": 1.0, "quality": "good"}
        )

    @pytest.mark.asyncio
    async def test_known_node_gets_write_with_good_status(self, sim):
        mock_node = MagicMock()
        mock_node.write_value = AsyncMock()
        sim.nodes["ns=2;s=real"] = mock_node

        await sim.handle_value_update(
            {"opc_node_id": "ns=2;s=real", "value": 1547.3, "quality": "good"}
        )

        mock_node.write_value.assert_awaited_once()
        data_value = mock_node.write_value.await_args.args[0]
        assert isinstance(data_value, ua.DataValue)
        assert data_value.Value.Value == pytest.approx(1547.3)
        assert data_value.StatusCode.is_good()

    @pytest.mark.asyncio
    async def test_bad_quality_flagged_on_node(self, sim):
        mock_node = MagicMock()
        mock_node.write_value = AsyncMock()
        sim.nodes["ns=2;s=flaky"] = mock_node

        await sim.handle_value_update(
            {"opc_node_id": "ns=2;s=flaky", "value": 0.0, "quality": "bad"}
        )

        data_value = mock_node.write_value.await_args.args[0]
        assert data_value.StatusCode.is_bad()

    @pytest.mark.asyncio
    async def test_missing_quality_defaults_to_good(self, sim):
        # The .get("quality", "good") fallback matters: older Django
        # code paths don't set quality and we don't want those
        # updates silently downgraded to Uncertain.
        mock_node = MagicMock()
        mock_node.write_value = AsyncMock()
        sim.nodes["ns=2;s=nokey"] = mock_node

        await sim.handle_value_update(
            {"opc_node_id": "ns=2;s=nokey", "value": 42.0}
        )

        data_value = mock_node.write_value.await_args.args[0]
        assert data_value.StatusCode.is_good()

    @pytest.mark.asyncio
    async def test_integer_value_coerced_to_double(self, sim):
        # All OPC-UA variables in this simulator are Double. A Python
        # int in the Redis payload must not raise — Django has sent
        # ints historically for level sensors.
        mock_node = MagicMock()
        mock_node.write_value = AsyncMock()
        sim.nodes["ns=2;s=int-sensor"] = mock_node

        await sim.handle_value_update(
            {"opc_node_id": "ns=2;s=int-sensor", "value": 5, "quality": "good"}
        )

        data_value = mock_node.write_value.await_args.args[0]
        assert data_value.Value.VariantType == ua.VariantType.Double
        assert data_value.Value.Value == pytest.approx(5.0)


# ──────────────────────────────────────────────────────────────
# Default device fallback
# ──────────────────────────────────────────────────────────────


class TestDefaultDevices:
    """When Django is unavailable, the simulator boots with a minimal
    device set so local demos still work. These tests pin that
    fallback so a refactor can't accidentally strand the server
    with zero nodes (which would silently look "healthy")."""

    def test_returns_nonempty_list(self, sim):
        devices = sim._get_default_devices()
        assert len(devices) > 0

    def test_each_device_has_required_fields(self, sim):
        required = {"device_id", "area", "line", "cell", "opc_node_id", "current_value"}
        for device in sim._get_default_devices():
            missing = required - device.keys()
            assert not missing, f"device missing fields: {missing}"

    def test_spans_multiple_areas(self, sim):
        # The local demo should exercise at least two ISA-95 areas
        # so the UI has something to show beyond a single plant row.
        areas = {d["area"] for d in sim._get_default_devices()}
        assert len(areas) >= 2

    def test_opc_node_ids_unique(self, sim):
        ids = [d["opc_node_id"] for d in sim._get_default_devices()]
        assert len(ids) == len(set(ids))
