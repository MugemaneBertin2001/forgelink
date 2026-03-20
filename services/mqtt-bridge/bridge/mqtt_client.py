"""MQTT to Kafka bridge implementation."""
import json
import logging
import re
from typing import Optional, Dict, Any

import paho.mqtt.client as mqtt
from confluent_kafka import Producer
from prometheus_client import Counter, Histogram, start_http_server

from bridge.config import settings

logger = logging.getLogger(__name__)

# Prometheus metrics
MESSAGES_RECEIVED = Counter(
    'mqtt_messages_received_total',
    'Total MQTT messages received',
    ['topic_type']
)
MESSAGES_PROCESSED = Counter(
    'mqtt_messages_processed_total',
    'Successfully processed messages',
    ['kafka_topic']
)
PARSE_ERRORS = Counter(
    'mqtt_parse_errors_total',
    'Messages that failed to parse'
)
KAFKA_LATENCY = Histogram(
    'kafka_publish_latency_seconds',
    'Time to publish to Kafka'
)
KAFKA_ERRORS = Counter(
    'kafka_publish_errors_total',
    'Failed Kafka publishes'
)


class MQTTBridge:
    """
    Bridges MQTT messages from EMQX to Kafka.
    Parses UNS topic hierarchy and routes to appropriate Kafka topics.
    """

    # UNS topic pattern: forgelink/<plant>/<area>/<line>/<cell>/<device_id>/<type>
    UNS_PATTERN = re.compile(
        r'^forgelink/(?P<plant>[^/]+)/(?P<area>[^/]+)/(?P<line>[^/]+)/'
        r'(?P<cell>[^/]+)/(?P<device_id>[^/]+)/(?P<type>telemetry|status|events|commands)$'
    )

    # Area to Kafka topic mapping
    TELEMETRY_TOPICS = {
        'melt-shop': 'telemetry.melt-shop',
        'continuous-casting': 'telemetry.continuous-casting',
        'rolling-mill': 'telemetry.rolling-mill',
        'finishing': 'telemetry.finishing',
    }

    def __init__(self):
        self.mqtt_client: Optional[mqtt.Client] = None
        self.kafka_producer: Optional[Producer] = None
        self._running = False

    def start(self):
        """Start the bridge."""
        # Start metrics server
        start_http_server(settings.metrics_port)
        logger.info(f"Metrics server started on port {settings.metrics_port}")

        # Initialize Kafka producer
        self.kafka_producer = Producer({
            'bootstrap.servers': settings.kafka_bootstrap_servers,
            'client.id': 'forgelink-mqtt-bridge',
        })

        # Initialize MQTT client
        self.mqtt_client = mqtt.Client(
            client_id="forgelink-mqtt-bridge",
            protocol=mqtt.MQTTv5
        )
        self.mqtt_client.username_pw_set(
            settings.emqx_mqtt_username,
            settings.emqx_mqtt_password
        )

        # Set callbacks
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.on_disconnect = self._on_disconnect

        # Connect and start loop
        self._running = True
        self.mqtt_client.connect(settings.emqx_host, settings.emqx_port)
        self.mqtt_client.loop_forever()

    def stop(self):
        """Stop the bridge."""
        self._running = False
        if self.mqtt_client:
            self.mqtt_client.disconnect()
        if self.kafka_producer:
            self.kafka_producer.flush()

    def _on_connect(self, client, userdata, flags, reason_code, properties):
        """Handle MQTT connection."""
        if reason_code == 0:
            logger.info("Connected to EMQX")
            client.subscribe(settings.mqtt_subscribe_topic)
            logger.info(f"Subscribed to {settings.mqtt_subscribe_topic}")
        else:
            logger.error(f"Connection failed: {reason_code}")

    def _on_disconnect(self, client, userdata, reason_code, properties):
        """Handle MQTT disconnection."""
        logger.warning(f"Disconnected from EMQX: {reason_code}")
        if self._running:
            logger.info("Attempting to reconnect...")

    def _on_message(self, client, userdata, msg):
        """Handle incoming MQTT message."""
        try:
            self._process_message(msg.topic, msg.payload)
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            PARSE_ERRORS.inc()

    def _process_message(self, topic: str, payload: bytes):
        """Process a single MQTT message."""
        # Parse topic
        match = self.UNS_PATTERN.match(topic)
        if not match:
            logger.warning(f"Unparseable topic: {topic}")
            self._publish_to_dlq(topic, payload)
            PARSE_ERRORS.inc()
            return

        topic_parts = match.groupdict()
        msg_type = topic_parts['type']
        area = topic_parts['area']

        MESSAGES_RECEIVED.labels(topic_type=msg_type).inc()

        # Parse payload
        try:
            data = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON payload for topic: {topic}")
            self._publish_to_dlq(topic, payload)
            PARSE_ERRORS.inc()
            return

        # Enrich payload with topic metadata
        data['_topic'] = topic
        data['_plant'] = topic_parts['plant']
        data['_area'] = area
        data['_line'] = topic_parts['line']
        data['_cell'] = topic_parts['cell']

        # Route to appropriate Kafka topic
        kafka_topic = self._get_kafka_topic(msg_type, area)
        self._publish_to_kafka(kafka_topic, topic_parts['device_id'], data)

    def _get_kafka_topic(self, msg_type: str, area: str) -> str:
        """Determine the Kafka topic for a message."""
        if msg_type == 'telemetry':
            return self.TELEMETRY_TOPICS.get(area, f'telemetry.{area}')
        elif msg_type == 'events':
            return 'events.all'
        elif msg_type == 'status':
            return 'status.all'
        elif msg_type == 'commands':
            return 'commands.all'
        else:
            return 'dlq.unparseable'

    def _publish_to_kafka(self, topic: str, key: str, data: Dict[str, Any]):
        """Publish a message to Kafka."""
        try:
            with KAFKA_LATENCY.time():
                self.kafka_producer.produce(
                    topic=topic,
                    key=key.encode('utf-8'),
                    value=json.dumps(data).encode('utf-8'),
                    callback=self._kafka_delivery_callback
                )
                self.kafka_producer.poll(0)

            MESSAGES_PROCESSED.labels(kafka_topic=topic).inc()

        except Exception as e:
            logger.error(f"Failed to publish to Kafka: {e}")
            KAFKA_ERRORS.inc()

    def _publish_to_dlq(self, topic: str, payload: bytes):
        """Publish unparseable message to dead letter queue."""
        try:
            data = {
                'original_topic': topic,
                'payload': payload.decode('utf-8', errors='replace'),
            }
            self.kafka_producer.produce(
                topic='dlq.unparseable',
                value=json.dumps(data).encode('utf-8'),
            )
            self.kafka_producer.poll(0)
        except Exception as e:
            logger.error(f"Failed to publish to DLQ: {e}")

    def _kafka_delivery_callback(self, err, msg):
        """Handle Kafka delivery confirmation."""
        if err:
            logger.error(f"Kafka delivery failed: {err}")
            KAFKA_ERRORS.inc()
