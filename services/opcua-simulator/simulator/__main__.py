"""Entry point for ForgeLink OPC-UA Simulation Server."""
import asyncio
import logging
import signal
import sys

from prometheus_client import start_http_server, Counter, Gauge

from .config import settings
from .server import OPCUASimulator
from .health import start_health_server

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

# Prometheus metrics
NODES_TOTAL = Gauge('opcua_nodes_total', 'Total OPC-UA nodes')
UPDATES_RECEIVED = Counter('opcua_updates_received_total', 'Value updates received from Redis')
UPDATE_ERRORS = Counter('opcua_update_errors_total', 'Value update errors')


async def main():
    """Main entry point."""
    logger.info("Starting ForgeLink OPC-UA Simulation Server")
    logger.info(f"OPC-UA Endpoint: {settings.opcua_endpoint}")
    logger.info(f"Redis: {settings.redis_url}")
    logger.info(f"Django API: {settings.django_api_url}")

    # Start metrics server
    start_http_server(settings.metrics_port)
    logger.info(f"Metrics server started on port {settings.metrics_port}")

    # Start health server
    await start_health_server(settings.health_port)
    logger.info(f"Health server started on port {settings.health_port}")

    # Create and start OPC-UA server
    simulator = OPCUASimulator()

    # Handle shutdown signals
    loop = asyncio.get_event_loop()

    def shutdown_handler():
        logger.info("Received shutdown signal")
        asyncio.create_task(simulator.stop())

    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown_handler)

    try:
        await simulator.start()
    except Exception as e:
        logger.error(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
