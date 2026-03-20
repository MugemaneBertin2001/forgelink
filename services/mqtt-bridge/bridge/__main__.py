"""ForgeLink MQTT Bridge entry point."""
import logging
import signal
import sys

from bridge.config import settings
from bridge.mqtt_client import MQTTBridge

logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point for the MQTT bridge."""
    logger.info("Starting ForgeLink MQTT Bridge")
    logger.info(f"EMQX: {settings.emqx_host}:{settings.emqx_port}")
    logger.info(f"Kafka: {settings.kafka_bootstrap_servers}")

    bridge = MQTTBridge()

    # Handle graceful shutdown
    def shutdown_handler(signum, frame):
        logger.info("Received shutdown signal")
        bridge.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    try:
        bridge.start()
    except Exception as e:
        logger.error(f"Bridge failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
