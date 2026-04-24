"""
OPC-UA Simulation Server for ForgeLink Steel Plant.

This server creates an OPC-UA address space that mirrors the ISA-95 equipment
hierarchy of the steel plant. It receives value updates from Django via Redis
pub/sub and updates the corresponding OPC-UA nodes.

Address Space Structure:
    Root/Objects/
        └── SteelPlantKigali/
            ├── MeltShop/
            │   ├── EAF1/
            │   │   ├── ElectrodeA/
            │   │   │   ├── TempSensor001 (value node)
            │   │   │   └── CurrentSensor001 (value node)
            │   │   └── ...
            │   └── ...
            ├── ContinuousCasting/
            ├── RollingMill/
            └── Finishing/
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any

from asyncua import Server, ua
from asyncua.common.node import Node
import redis.asyncio as redis

from .config import settings
from .correlation import (
    bind as bind_correlation,
    clear as clear_correlation,
    new_correlation_id,
)

logger = logging.getLogger(__name__)


class OPCUASimulator:
    """
    OPC-UA Server that simulates steel plant PLCs.

    Creates address space nodes for all devices and updates values
    received from Django Celery tasks via Redis pub/sub.
    """

    def __init__(self):
        self.server: Optional[Server] = None
        self.redis: Optional[redis.Redis] = None
        self.nodes: Dict[str, Node] = {}  # Map opc_node_id -> Node
        self.namespace_idx: int = 0
        self._running = False

    async def init_server(self):
        """Initialize the OPC-UA server."""
        self.server = Server()
        await self.server.init()

        # Configure server
        self.server.set_endpoint(settings.opcua_endpoint)
        self.server.set_server_name(settings.opcua_server_name)

        # Security - disable for development (enable mTLS for production)
        self.server.set_security_policy([ua.SecurityPolicyType.NoSecurity])

        # Register namespace
        self.namespace_idx = await self.server.register_namespace(settings.opcua_namespace)

        logger.info(f"OPC-UA server initialized at {settings.opcua_endpoint}")

    async def build_address_space(self, devices: list):
        """
        Build the OPC-UA address space from device list.

        Creates folder nodes for the ISA-95 hierarchy and variable nodes
        for each device value.
        """
        objects = self.server.nodes.objects

        # Create plant root node
        plant_name = settings.plant_name.replace('-', '').title().replace(' ', '')
        plant_node = await objects.add_folder(
            self.namespace_idx,
            plant_name
        )

        # Track created folder nodes to avoid duplicates
        folder_cache: Dict[str, Node] = {plant_name: plant_node}

        for device in devices:
            # Build path: Area/Line/Cell
            area = device.get('area', '').replace('-', '').title().replace(' ', '')
            line = device.get('line', '').replace('-', '').title().replace(' ', '')
            cell = device.get('cell', '').replace('-', '').title().replace(' ', '')
            device_id = device.get('device_id', '').replace('-', '').title().replace(' ', '')

            # Create area folder if needed
            area_path = f"{plant_name}/{area}"
            if area_path not in folder_cache and area:
                folder_cache[area_path] = await folder_cache[plant_name].add_folder(
                    self.namespace_idx, area
                )

            # Create line folder if needed
            line_path = f"{area_path}/{line}"
            if line_path not in folder_cache and line:
                folder_cache[line_path] = await folder_cache[area_path].add_folder(
                    self.namespace_idx, line
                )

            # Create cell folder if needed
            if cell:
                cell_path = f"{line_path}/{cell}"
                if cell_path not in folder_cache:
                    folder_cache[cell_path] = await folder_cache[line_path].add_folder(
                        self.namespace_idx, cell
                    )
                parent_folder = folder_cache[cell_path]
            else:
                parent_folder = folder_cache[line_path]

            # Create device value node
            initial_value = float(device.get('current_value') or 0.0)
            opc_node_id = device.get('opc_node_id', f"ns={self.namespace_idx};s={device_id}")

            var_node = await parent_folder.add_variable(
                self.namespace_idx,
                device_id,
                initial_value,
                varianttype=ua.VariantType.Double
            )

            # Make it writable (for simulation control)
            await var_node.set_writable()

            # Store reference
            self.nodes[opc_node_id] = var_node

            logger.debug(f"Created node: {opc_node_id}")

        logger.info(f"Built address space with {len(self.nodes)} device nodes")

    async def fetch_devices_from_django(self) -> list:
        """Fetch device list from Django API."""
        import httpx

        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.django_api_url}/api/simulator/devices/",
                    timeout=30.0
                )
                if response.status_code == 200:
                    data = response.json()
                    # Handle paginated or list response
                    if isinstance(data, dict) and 'results' in data:
                        return data['results']
                    return data
                else:
                    logger.warning(f"Django API returned {response.status_code}")
        except Exception as e:
            logger.error(f"Failed to fetch devices from Django: {e}")

        return []

    async def connect_redis(self):
        """Connect to Redis for pub/sub."""
        self.redis = redis.from_url(settings.redis_url)
        logger.info(f"Connected to Redis at {settings.redis_url}")

    async def subscribe_to_updates(self):
        """Subscribe to Redis channel for value updates."""
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(settings.redis_channel)

        logger.info(f"Subscribed to Redis channel: {settings.redis_channel}")

        async for message in pubsub.listen():
            if not self._running:
                break

            if message['type'] == 'message':
                try:
                    data = json.loads(message['data'])
                    await self.handle_value_update(data)
                except json.JSONDecodeError:
                    logger.warning("Received invalid JSON from Redis")
                except Exception as e:
                    logger.error(f"Error handling value update: {e}")

    async def handle_value_update(self, data: Dict[str, Any]):
        """
        Handle a value update from Django.

        Expected data format:
        {
            "device_id": "uuid",
            "opc_node_id": "ns=2;s=...",
            "mqtt_topic": "forgelink/...",
            "value": 1547.3,
            "quality": "good",
            "timestamp": "2024-03-20T14:30:00Z",
            "sequence": 10482,
            "unit": "celsius",
            "correlation_id": "..."   # optional — honored if present
        }
        """
        # Honor an incoming correlation_id so a trace that started in
        # Django continues here; otherwise mint one so log lines for
        # this single update are still groupable.
        bind_correlation(
            data.get("correlation_id") or new_correlation_id()
        )

        opc_node_id = data.get('opc_node_id')
        value = data.get('value')
        quality = data.get('quality', 'good')

        if opc_node_id not in self.nodes:
            logger.debug(f"Unknown node: {opc_node_id}")
            clear_correlation()
            return

        node = self.nodes[opc_node_id]

        # Update value. asyncua's DataValue.__init__ uses ``StatusCode_``
        # (trailing underscore) to avoid shadowing the ``ua.StatusCode``
        # type in its own dataclass; passing ``StatusCode=`` raises
        # TypeError at runtime for every update.
        now = datetime.now(timezone.utc)
        try:
            await node.write_value(ua.DataValue(
                Value=ua.Variant(float(value), ua.VariantType.Double),
                StatusCode_=self._quality_to_status(quality),
                SourceTimestamp=now,
                ServerTimestamp=now
            ))

            logger.debug(f"Updated {opc_node_id} = {value} ({quality})")
        finally:
            clear_correlation()

    def _quality_to_status(self, quality: str) -> ua.StatusCode:
        """Convert quality string to OPC-UA StatusCode."""
        if quality == 'good':
            return ua.StatusCode(ua.StatusCodes.Good)
        elif quality == 'bad':
            return ua.StatusCode(ua.StatusCodes.Bad)
        else:
            return ua.StatusCode(ua.StatusCodes.Uncertain)

    async def start(self):
        """Start the OPC-UA server."""
        self._running = True

        # Initialize server
        await self.init_server()

        # Fetch devices from Django
        logger.info("Fetching devices from Django API...")
        devices = await self.fetch_devices_from_django()

        if not devices:
            logger.warning("No devices found, creating minimal address space")
            devices = self._get_default_devices()

        # Build address space
        await self.build_address_space(devices)

        # Start OPC-UA server
        async with self.server:
            logger.info("OPC-UA server started")

            # Connect to Redis
            await self.connect_redis()

            # Subscribe to value updates
            await self.subscribe_to_updates()

    async def stop(self):
        """Stop the OPC-UA server."""
        self._running = False

        if self.redis:
            await self.redis.close()

        logger.info("OPC-UA server stopped")

    def _get_default_devices(self) -> list:
        """Return default device list if Django API is unavailable."""
        return [
            {
                'device_id': 'temp-sensor-001',
                'area': 'melt-shop',
                'line': 'eaf-1',
                'cell': 'electrode-a',
                'current_value': 1550.0,
                'opc_node_id': 'ns=2;s=steelplantkigali/meltshop/eaf1/electrodea/tempsensor001'
            },
            {
                'device_id': 'temp-sensor-002',
                'area': 'melt-shop',
                'line': 'eaf-1',
                'cell': 'electrode-b',
                'current_value': 1545.0,
                'opc_node_id': 'ns=2;s=steelplantkigali/meltshop/eaf1/electrodeb/tempsensor002'
            },
            {
                'device_id': 'level-sensor-011',
                'area': 'continuous-casting',
                'line': 'caster-1',
                'cell': 'mold',
                'current_value': 0.5,
                'opc_node_id': 'ns=2;s=steelplantkigali/continuouscasting/caster1/mold/levelsensor011'
            },
        ]
