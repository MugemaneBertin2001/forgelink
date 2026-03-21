"""
Kafka consumer for telemetry data ingestion.

Consumes telemetry messages from Kafka topics and writes them to TDengine.
Designed to run as a separate process alongside Django.
"""
import json
import logging
import signal
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from confluent_kafka import Consumer, KafkaError, KafkaException
from django.conf import settings

from .tdengine import insert_telemetry_batch, get_tdengine_client
from .services import TelemetryService

logger = logging.getLogger(__name__)


@dataclass
class TelemetryMessage:
    """Parsed telemetry message from Kafka."""
    device_id: str
    value: float
    quality: str
    timestamp: str
    plant: str
    area: str
    line: Optional[str] = None
    cell: Optional[str] = None
    unit: Optional[str] = None
    sequence: int = 0

    def to_record(self) -> Dict[str, Any]:
        """Convert to TDengine record format."""
        return {
            'device_id': self.device_id,
            'ts': self.timestamp,
            'value': self.value,
            'quality': self.quality,
            'plant': self.plant,
            'area': self.area,
            'line': self.line or '',
            'cell': self.cell or '',
            'unit': self.unit or '',
            'sequence': self.sequence,
        }


class TelemetryKafkaConsumer:
    """
    Kafka consumer for telemetry data.

    Consumes from telemetry topics and batches writes to TDengine.
    """

    def __init__(
        self,
        bootstrap_servers: str = None,
        group_id: str = 'forgelink-telemetry-consumer',
        topics: List[str] = None,
        batch_size: int = 500,
        batch_timeout_ms: int = 1000,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.group_id = group_id
        self.topics = topics or [
            'telemetry.melt-shop',
            'telemetry.continuous-casting',
            'telemetry.rolling-mill',
            'telemetry.finishing',
        ]
        self.batch_size = batch_size
        self.batch_timeout_ms = batch_timeout_ms

        self.consumer: Optional[Consumer] = None
        self.running = False
        self.batch: List[Dict[str, Any]] = []
        self.last_flush_time = time.time()

        # Statistics
        self.stats = {
            'messages_received': 0,
            'messages_processed': 0,
            'batches_written': 0,
            'errors': 0,
            'start_time': None,
        }

    def create_consumer(self) -> Consumer:
        """Create Kafka consumer instance."""
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'latest',
            'enable.auto.commit': True,
            'auto.commit.interval.ms': 5000,
            'session.timeout.ms': 30000,
            'max.poll.interval.ms': 300000,
            'fetch.min.bytes': 1,
            'fetch.wait.max.ms': 500,
        }

        # Add security config if present
        security_protocol = getattr(settings, 'KAFKA_SECURITY_PROTOCOL', None)
        if security_protocol:
            config['security.protocol'] = security_protocol

        sasl_mechanism = getattr(settings, 'KAFKA_SASL_MECHANISM', None)
        if sasl_mechanism:
            config['sasl.mechanism'] = sasl_mechanism
            config['sasl.username'] = getattr(settings, 'KAFKA_SASL_USERNAME', '')
            config['sasl.password'] = getattr(settings, 'KAFKA_SASL_PASSWORD', '')

        return Consumer(config)

    def parse_message(self, msg_value: bytes) -> Optional[TelemetryMessage]:
        """Parse Kafka message to TelemetryMessage."""
        try:
            data = json.loads(msg_value.decode('utf-8'))

            # Handle different message formats
            # Format 1: Direct telemetry
            if 'device_id' in data:
                return TelemetryMessage(
                    device_id=data['device_id'],
                    value=float(data['value']),
                    quality=data.get('quality', 'good'),
                    timestamp=data.get('ts') or data.get('timestamp') or datetime.now(timezone.utc).isoformat(),
                    plant=data.get('plant', 'steel-plant-kigali'),
                    area=data.get('area', ''),
                    line=data.get('line'),
                    cell=data.get('cell'),
                    unit=data.get('unit'),
                    sequence=data.get('sequence', 0),
                )

            # Format 2: UNS payload (from Edge Gateway)
            if 'payload' in data:
                payload = data['payload']
                topic_parts = data.get('topic', '').split('/')
                # forgelink/plant/area/line/cell/device/type
                plant = topic_parts[1] if len(topic_parts) > 1 else 'steel-plant-kigali'
                area = topic_parts[2] if len(topic_parts) > 2 else ''
                line = topic_parts[3] if len(topic_parts) > 3 else None
                cell = topic_parts[4] if len(topic_parts) > 4 else None
                device_id = topic_parts[5] if len(topic_parts) > 5 else payload.get('device_id', 'unknown')

                return TelemetryMessage(
                    device_id=device_id,
                    value=float(payload.get('value', 0)),
                    quality=payload.get('quality', 'good'),
                    timestamp=payload.get('ts') or datetime.now(timezone.utc).isoformat(),
                    plant=plant,
                    area=area,
                    line=line,
                    cell=cell,
                    unit=payload.get('unit'),
                    sequence=payload.get('sequence', 0),
                )

            logger.warning(f"Unknown message format: {data}")
            return None

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse telemetry message: {e}")
            return None

    def flush_batch(self):
        """Flush current batch to TDengine."""
        if not self.batch:
            return

        try:
            count = insert_telemetry_batch(self.batch)
            self.stats['batches_written'] += 1
            self.stats['messages_processed'] += len(self.batch)
            logger.debug(f"Flushed batch of {len(self.batch)} records to TDengine")
        except Exception as e:
            logger.error(f"Failed to flush batch to TDengine: {e}")
            self.stats['errors'] += 1
            # TODO: Implement retry logic or dead letter queue
        finally:
            self.batch = []
            self.last_flush_time = time.time()

    def should_flush(self) -> bool:
        """Check if batch should be flushed."""
        if len(self.batch) >= self.batch_size:
            return True

        elapsed_ms = (time.time() - self.last_flush_time) * 1000
        if elapsed_ms >= self.batch_timeout_ms and self.batch:
            return True

        return False

    def process_message(self, msg):
        """Process a single Kafka message."""
        self.stats['messages_received'] += 1

        telemetry = self.parse_message(msg.value())
        if telemetry:
            self.batch.append(telemetry.to_record())

        if self.should_flush():
            self.flush_batch()

    def start(self):
        """Start consuming messages."""
        logger.info(f"Starting Kafka consumer for topics: {self.topics}")
        self.stats['start_time'] = datetime.now(timezone.utc)

        self.consumer = self.create_consumer()
        self.consumer.subscribe(self.topics)
        self.running = True

        # Setup signal handlers
        def signal_handler(sig, frame):
            logger.info(f"Received signal {sig}, shutting down...")
            self.stop()

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            while self.running:
                msg = self.consumer.poll(timeout=0.1)

                if msg is None:
                    # Check if we need to flush due to timeout
                    if self.should_flush():
                        self.flush_batch()
                    continue

                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, not an error
                        continue
                    else:
                        logger.error(f"Kafka error: {msg.error()}")
                        self.stats['errors'] += 1
                        continue

                self.process_message(msg)

        except KafkaException as e:
            logger.error(f"Kafka exception: {e}")
            self.stats['errors'] += 1
        finally:
            self.shutdown()

    def stop(self):
        """Signal consumer to stop."""
        self.running = False

    def shutdown(self):
        """Clean shutdown."""
        logger.info("Shutting down Kafka consumer...")

        # Flush any remaining messages
        if self.batch:
            logger.info(f"Flushing final batch of {len(self.batch)} messages")
            self.flush_batch()

        # Close consumer
        if self.consumer:
            self.consumer.close()
            self.consumer = None

        # Log final statistics
        self.log_stats()
        logger.info("Kafka consumer shutdown complete")

    def log_stats(self):
        """Log consumer statistics."""
        duration = None
        if self.stats['start_time']:
            duration = (datetime.now(timezone.utc) - self.stats['start_time']).total_seconds()

        logger.info(
            f"Consumer stats: "
            f"received={self.stats['messages_received']}, "
            f"processed={self.stats['messages_processed']}, "
            f"batches={self.stats['batches_written']}, "
            f"errors={self.stats['errors']}, "
            f"duration={duration:.2f}s" if duration else ""
        )


class EventKafkaConsumer:
    """
    Kafka consumer for event/status messages.

    Consumes from event topics and processes alerts, status updates.
    """

    def __init__(
        self,
        bootstrap_servers: str = None,
        group_id: str = 'forgelink-event-consumer',
        topics: List[str] = None,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.group_id = group_id
        self.topics = topics or ['events.all', 'status.all']
        self.consumer: Optional[Consumer] = None
        self.running = False

    def create_consumer(self) -> Consumer:
        """Create Kafka consumer instance."""
        config = {
            'bootstrap.servers': self.bootstrap_servers,
            'group.id': self.group_id,
            'auto.offset.reset': 'latest',
            'enable.auto.commit': True,
        }
        return Consumer(config)

    def process_event(self, msg):
        """Process an event message."""
        try:
            data = json.loads(msg.value().decode('utf-8'))
            event_type = data.get('event_type')

            if event_type in ['threshold_high', 'threshold_low', 'critical_high', 'critical_low']:
                # Record threshold event in TDengine
                from .tdengine import insert_event
                insert_event(
                    device_id=data.get('device_id'),
                    plant=data.get('plant', 'steel-plant-kigali'),
                    area=data.get('area', ''),
                    event_type=event_type,
                    severity=data.get('severity', 'medium'),
                    message=data.get('message', ''),
                    value=data.get('value'),
                    threshold=data.get('threshold'),
                )
                logger.info(f"Recorded event: {event_type} for {data.get('device_id')}")

            elif event_type in ['device_online', 'device_offline', 'device_fault']:
                # Update device status
                from apps.assets.models import Device
                try:
                    device = Device.objects.get(device_id=data.get('device_id'))
                    status_map = {
                        'device_online': 'online',
                        'device_offline': 'offline',
                        'device_fault': 'fault',
                    }
                    device.update_status(status_map.get(event_type, 'unknown'))
                    logger.info(f"Updated device status: {device.device_id} -> {status_map.get(event_type)}")
                except Device.DoesNotExist:
                    logger.warning(f"Device not found: {data.get('device_id')}")

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse event JSON: {e}")
        except Exception as e:
            logger.error(f"Failed to process event: {e}")

    def start(self):
        """Start consuming events."""
        logger.info(f"Starting event consumer for topics: {self.topics}")

        self.consumer = self.create_consumer()
        self.consumer.subscribe(self.topics)
        self.running = True

        signal.signal(signal.SIGINT, lambda s, f: self.stop())
        signal.signal(signal.SIGTERM, lambda s, f: self.stop())

        try:
            while self.running:
                msg = self.consumer.poll(timeout=1.0)

                if msg is None:
                    continue

                if msg.error():
                    if msg.error().code() != KafkaError._PARTITION_EOF:
                        logger.error(f"Kafka error: {msg.error()}")
                    continue

                self.process_event(msg)

        except KafkaException as e:
            logger.error(f"Kafka exception: {e}")
        finally:
            if self.consumer:
                self.consumer.close()

    def stop(self):
        """Signal consumer to stop."""
        self.running = False


def run_telemetry_consumer():
    """Entry point for telemetry consumer."""
    import django
    django.setup()

    consumer = TelemetryKafkaConsumer()
    consumer.start()


def run_event_consumer():
    """Entry point for event consumer."""
    import django
    django.setup()

    consumer = EventKafkaConsumer()
    consumer.start()
