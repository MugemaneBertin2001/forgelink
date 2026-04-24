"""Entry point for ForgeLink Edge Gateway."""
import asyncio
import logging
import signal
import sys

from prometheus_client import start_http_server, Counter, Gauge

from .config import settings
from .bridge import EdgeGateway
from .health import start_health_server, set_opcua_status, set_mqtt_status
from .logging_setup import configure as configure_logging

# Must run before any other module's first log call.
configure_logging(level=settings.log_level)
logger = logging.getLogger(__name__)

# Prometheus metrics
MESSAGES_PUBLISHED = Counter(
    'edge_messages_published_total',
    'Total messages published to MQTT'
)
MESSAGES_BUFFERED = Counter(
    'edge_messages_buffered_total',
    'Messages buffered during MQTT disconnect'
)
BUFFER_SIZE = Gauge(
    'edge_buffer_size',
    'Current buffer size'
)
OPCUA_CONNECTED = Gauge(
    'edge_opcua_connected',
    'OPC-UA connection status'
)
MQTT_CONNECTED = Gauge(
    'edge_mqtt_connected',
    'MQTT connection status'
)


async def main():
    """Main entry point."""
    logger.info("Starting ForgeLink Edge Gateway")
    logger.info(f"OPC-UA Server: {settings.opcua_endpoint}")
    logger.info(f"MQTT Broker: {settings.mqtt_host}:{settings.mqtt_port}")

    # Start metrics server
    start_http_server(settings.metrics_port)
    logger.info(f"Metrics server started on port {settings.metrics_port}")

    # Start health server
    await start_health_server(settings.health_port)
    logger.info(f"Health server started on port {settings.health_port}")

    # Create and start gateway
    gateway = EdgeGateway()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(gateway.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    try:
        await gateway.start()
    except Exception as e:
        logger.error(f"Gateway failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
