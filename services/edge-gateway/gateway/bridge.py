"""
Edge Gateway - OPC-UA to MQTT Bridge.

This service:
1. Connects to OPC-UA server (simulated PLCs)
2. Subscribes to value changes on all device nodes
3. Transforms OPC-UA data to UNS MQTT format
4. Publishes to EMQX broker

The bridge handles:
- Automatic reconnection to OPC-UA and MQTT
- Message buffering during disconnects
- Dead-band filtering to reduce traffic
- Quality code translation
"""
import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Optional, Any, List
from collections import deque
from dataclasses import dataclass

from asyncua import Client, ua
from asyncua.common.subscription import Subscription, DataChangeNotif
import paho.mqtt.client as mqtt

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class BufferedMessage:
    """Message buffered during MQTT disconnect."""
    topic: str
    payload: str
    timestamp: datetime


class EdgeGateway:
    """
    Bridges OPC-UA server to MQTT broker.

    Subscribes to all device nodes in the OPC-UA server and publishes
    value changes to corresponding MQTT topics following the UNS structure.
    """

    def __init__(self):
        self.opcua_client: Optional[Client] = None
        self.mqtt_client: Optional[mqtt.Client] = None
        self.subscription: Optional[Subscription] = None

        # Node mapping: opc_node_id -> mqtt_topic
        self.node_mapping: Dict[str, str] = {}

        # Message buffer for handling disconnects
        self.buffer: deque = deque(maxlen=settings.buffer_size)

        # State
        self._running = False
        self._opcua_connected = False
        self._mqtt_connected = False

        # Last values for dead-band filtering
        self._last_values: Dict[str, float] = {}

        # Sequence counters
        self._sequences: Dict[str, int] = {}

        # Asyncio event loop captured at start() time so that paho's
        # network-thread callbacks can schedule coroutines back onto it
        # with asyncio.run_coroutine_threadsafe. Calling asyncio.create_task
        # or asyncio.get_event_loop() from a non-loop thread raises
        # RuntimeError at runtime.
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    async def start(self):
        """Start the edge gateway."""
        self._running = True

        # Capture the running event loop so MQTT-thread callbacks can
        # marshal work back onto it safely.
        self._loop = asyncio.get_running_loop()

        # Start MQTT client
        self._setup_mqtt()
        self._connect_mqtt()

        # Main loop
        while self._running:
            try:
                await self._run_opcua_loop()
            except Exception as e:
                logger.error(f"OPC-UA loop error: {e}")
                await asyncio.sleep(settings.opcua_reconnect_interval)

    async def stop(self):
        """Stop the edge gateway."""
        self._running = False

        if self.subscription:
            await self.subscription.delete()

        if self.opcua_client:
            await self.opcua_client.disconnect()

        if self.mqtt_client:
            self.mqtt_client.disconnect()
            self.mqtt_client.loop_stop()

        logger.info("Edge Gateway stopped")

    def _setup_mqtt(self):
        """Setup MQTT client."""
        self.mqtt_client = mqtt.Client(
            client_id=settings.mqtt_client_id,
            protocol=mqtt.MQTTv5
        )
        self.mqtt_client.username_pw_set(
            settings.mqtt_username,
            settings.mqtt_password
        )

        # Callbacks
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_disconnect = self._on_mqtt_disconnect

        # Start network loop in background thread
        self.mqtt_client.loop_start()

    def _connect_mqtt(self):
        """Connect to MQTT broker."""
        try:
            self.mqtt_client.connect(
                settings.mqtt_host,
                settings.mqtt_port
            )
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")

    def _on_mqtt_connect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT connection. Called from paho's network thread."""
        if reason_code == 0:
            logger.info("Connected to MQTT broker")
            self._mqtt_connected = True
            # Schedule the async buffer flush on the captured event loop.
            # asyncio.create_task() would raise RuntimeError when called
            # from a thread that is not the loop's owner.
            if self._loop is not None:
                asyncio.run_coroutine_threadsafe(self._flush_buffer(), self._loop)
        else:
            logger.error(f"MQTT connection failed: {reason_code}")

    def _on_mqtt_disconnect(self, client, userdata, reason_code, properties):
        """Handle MQTT disconnection. Called from paho's network thread."""
        logger.warning(f"Disconnected from MQTT broker: {reason_code}")
        self._mqtt_connected = False

        # Reconnect via the captured loop — asyncio.get_event_loop() is
        # deprecated in 3.12 and raises when there is no running loop in
        # the current (non-asyncio) thread.
        if self._running and self._loop is not None:
            self._loop.call_soon_threadsafe(
                lambda: self._loop.call_later(
                    settings.mqtt_reconnect_interval,
                    self._connect_mqtt,
                )
            )

    async def _run_opcua_loop(self):
        """Main OPC-UA connection and subscription loop."""
        # Connect to OPC-UA server
        self.opcua_client = Client(settings.opcua_endpoint)

        try:
            await self.opcua_client.connect()
            logger.info(f"Connected to OPC-UA server: {settings.opcua_endpoint}")
            self._opcua_connected = True

            # Discover nodes and create subscriptions
            await self._discover_and_subscribe()

            # Keep connection alive
            while self._running and self._opcua_connected:
                await asyncio.sleep(1)

        except Exception as e:
            logger.error(f"OPC-UA error: {e}")
            self._opcua_connected = False
        finally:
            if self.opcua_client:
                try:
                    await self.opcua_client.disconnect()
                except:
                    pass

    async def _discover_and_subscribe(self):
        """Discover device nodes and create subscriptions."""
        # Get namespace index
        namespace_idx = await self.opcua_client.get_namespace_index(
            settings.opcua_namespace
        )

        # Browse to find all device nodes
        objects = self.opcua_client.nodes.objects
        device_nodes = await self._browse_for_variables(objects, namespace_idx)

        if not device_nodes:
            logger.warning("No device nodes found in OPC-UA server")
            return

        logger.info(f"Found {len(device_nodes)} device nodes")

        # Create subscription
        self.subscription = await self.opcua_client.create_subscription(
            settings.subscription_interval,
            self
        )

        # Subscribe to all device nodes
        for node, node_path in device_nodes:
            mqtt_topic = self._path_to_mqtt_topic(node_path)
            node_id = node.nodeid.to_string()

            self.node_mapping[node_id] = mqtt_topic
            self._sequences[node_id] = 0

            await self.subscription.subscribe_data_change(
                node,
                queuesize=settings.queue_size
            )

            logger.debug(f"Subscribed: {node_id} -> {mqtt_topic}")

        logger.info(f"Created subscriptions for {len(device_nodes)} nodes")

    async def _browse_for_variables(self, node, namespace_idx: int,
                                     path: str = "") -> List[tuple]:
        """Recursively browse for variable nodes."""
        variables = []

        try:
            children = await node.get_children()

            for child in children:
                child_name = await child.read_browse_name()

                # Only process nodes in our namespace
                if child_name.NamespaceIndex != namespace_idx:
                    continue

                name = child_name.Name
                child_path = f"{path}/{name}" if path else name

                # Check node class
                node_class = await child.read_node_class()

                if node_class == ua.NodeClass.Variable:
                    variables.append((child, child_path))
                elif node_class == ua.NodeClass.Object:
                    # Recurse into folder
                    sub_vars = await self._browse_for_variables(
                        child, namespace_idx, child_path
                    )
                    variables.extend(sub_vars)

        except Exception as e:
            logger.warning(f"Error browsing node: {e}")

        return variables

    def _path_to_mqtt_topic(self, opc_path: str) -> str:
        """
        Convert OPC-UA path to MQTT topic.

        OPC-UA: SteelPlantKigali/MeltShop/EAF1/ElectrodeA/TempSensor001
        MQTT:   forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry
        """
        # Split path and convert to kebab-case
        parts = opc_path.split('/')
        converted = []

        for part in parts:
            # Convert CamelCase to kebab-case
            kebab = ''
            for i, char in enumerate(part):
                if char.isupper() and i > 0:
                    kebab += '-'
                kebab += char.lower()
            converted.append(kebab)

        # Build UNS topic
        topic_parts = [settings.uns_root]

        # Map to ISA-95 levels
        if len(converted) >= 1:
            topic_parts.append(converted[0])  # Plant
        if len(converted) >= 2:
            topic_parts.append(converted[1])  # Area
        if len(converted) >= 3:
            topic_parts.append(converted[2])  # Line
        if len(converted) >= 4:
            topic_parts.append(converted[3])  # Cell
        if len(converted) >= 5:
            topic_parts.append(converted[4])  # Device

        topic_parts.append('telemetry')

        return '/'.join(topic_parts)

    async def datachange_notification(self, node, val, data: DataChangeNotif):
        """
        Handle OPC-UA data change notification.

        Called by asyncua when a subscribed node value changes.
        """
        try:
            node_id = node.nodeid.to_string()

            if node_id not in self.node_mapping:
                return

            # Get value and status
            value = float(val) if val is not None else 0.0
            quality = self._status_to_quality(data.monitored_item.Value.StatusCode)

            # Dead-band filtering
            if settings.dead_band > 0:
                last_value = self._last_values.get(node_id)
                if last_value is not None and abs(value - last_value) < settings.dead_band:
                    return

            self._last_values[node_id] = value

            # Increment sequence
            self._sequences[node_id] += 1

            # Build message
            mqtt_topic = self.node_mapping[node_id]
            device_id = mqtt_topic.split('/')[-2]  # Second to last part

            message = {
                "device_id": device_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": value,
                "quality": quality,
                "sequence": self._sequences[node_id]
            }

            # Publish or buffer
            payload = json.dumps(message)

            if self._mqtt_connected:
                self.mqtt_client.publish(
                    mqtt_topic,
                    payload,
                    qos=0  # Telemetry uses QoS 0
                )
                logger.debug(f"Published: {mqtt_topic} = {value}")
            else:
                # Buffer message for later
                self.buffer.append(BufferedMessage(
                    topic=mqtt_topic,
                    payload=payload,
                    timestamp=datetime.now(timezone.utc)
                ))
                logger.debug(f"Buffered: {mqtt_topic}")

        except Exception as e:
            logger.error(f"Error processing data change: {e}")

    def _status_to_quality(self, status_code) -> str:
        """Convert OPC-UA StatusCode to quality string."""
        if status_code.is_good():
            return "good"
        elif status_code.is_bad():
            return "bad"
        else:
            return "uncertain"

    async def _flush_buffer(self):
        """Flush buffered messages when MQTT reconnects."""
        flushed = 0

        while self.buffer and self._mqtt_connected:
            msg = self.buffer.popleft()
            self.mqtt_client.publish(msg.topic, msg.payload, qos=0)
            flushed += 1

            # Small delay to avoid overwhelming broker
            if flushed % 100 == 0:
                await asyncio.sleep(0.01)

        if flushed:
            logger.info(f"Flushed {flushed} buffered messages")
