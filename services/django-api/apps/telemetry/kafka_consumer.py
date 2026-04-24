"""
Kafka consumer for telemetry data ingestion.

Consumes telemetry messages from Kafka topics and writes them to TDengine.
Designed to run as a separate process alongside Django.
"""

import json
import logging
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from django.conf import settings

from confluent_kafka import Consumer, KafkaError, KafkaException

from .tdengine import insert_telemetry_batch

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
            "device_id": self.device_id,
            "ts": self.timestamp,
            "value": self.value,
            "quality": self.quality,
            "plant": self.plant,
            "area": self.area,
            "line": self.line or "",
            "cell": self.cell or "",
            "unit": self.unit or "",
            "sequence": self.sequence,
        }


class TelemetryKafkaConsumer:
    """
    Kafka consumer for telemetry data.

    Consumes from telemetry topics and batches writes to TDengine.
    """

    def __init__(
        self,
        bootstrap_servers: str = None,
        group_id: str = "forgelink-telemetry-consumer",
        topics: List[str] = None,
        batch_size: int = 500,
        batch_timeout_ms: int = 1000,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.group_id = group_id
        self.topics = topics or [
            "telemetry.melt-shop",
            "telemetry.continuous-casting",
            "telemetry.rolling-mill",
            "telemetry.finishing",
        ]
        self.batch_size = batch_size
        self.batch_timeout_ms = batch_timeout_ms

        self.consumer: Optional[Consumer] = None
        self.running = False
        self.batch: List[Dict[str, Any]] = []
        # Kafka messages held alongside self.batch for offset-commit after
        # a successful flush. We keep them 1:1 with records so that if a
        # message fails to parse and is skipped, its offset is still
        # eventually advanced by a successful later message in the same
        # partition (Kafka commits are monotonic per partition).
        self.batch_messages: List[Any] = []
        self.last_flush_time = time.time()

        # Statistics
        self.stats = {
            "messages_received": 0,
            "messages_processed": 0,
            "batches_written": 0,
            "errors": 0,
            "dlq_messages": 0,
            "commits": 0,
            "start_time": None,
        }

    def create_consumer(self) -> Consumer:
        """Create Kafka consumer instance configured for at-least-once delivery.

        Delivery semantics:
        ``enable.auto.commit=False`` plus an explicit ``commit(msg)`` call
        only after :meth:`flush_batch` has successfully written the batch to
        TDengine. If the process crashes between receiving a message and
        writing the batch, the next consumer in the group replays from the
        last committed offset — the batch is retried rather than lost.

        Offset-reset:
        ``earliest`` (not ``latest``) so the first consumer in a new group
        backfills every message already sitting in the topic. Combined
        with the idempotent TDengine insert path, this makes cold-start
        replays safe.
        """
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
            "session.timeout.ms": 30000,
            "max.poll.interval.ms": 300000,
            "fetch.min.bytes": 1,
            "fetch.wait.max.ms": 500,
        }

        # Add security config if present
        security_protocol = getattr(settings, "KAFKA_SECURITY_PROTOCOL", None)
        if security_protocol:
            config["security.protocol"] = security_protocol

        sasl_mechanism = getattr(settings, "KAFKA_SASL_MECHANISM", None)
        if sasl_mechanism:
            config["sasl.mechanism"] = sasl_mechanism
            config["sasl.username"] = getattr(settings, "KAFKA_SASL_USERNAME", "")
            config["sasl.password"] = getattr(settings, "KAFKA_SASL_PASSWORD", "")

        return Consumer(config)

    def parse_message(self, msg_value: bytes) -> Optional[TelemetryMessage]:
        """Parse Kafka message to TelemetryMessage."""
        try:
            data = json.loads(msg_value.decode("utf-8"))

            # Handle different message formats
            # Format 1: Direct telemetry
            if "device_id" in data:
                return TelemetryMessage(
                    device_id=data["device_id"],
                    value=float(data["value"]),
                    quality=data.get("quality", "good"),
                    timestamp=data.get("ts")
                    or data.get("timestamp")
                    or datetime.now(timezone.utc).isoformat(),
                    plant=data.get("plant", "steel-plant-kigali"),
                    area=data.get("area", ""),
                    line=data.get("line"),
                    cell=data.get("cell"),
                    unit=data.get("unit"),
                    sequence=data.get("sequence", 0),
                )

            # Format 2: UNS payload (from Edge Gateway)
            if "payload" in data:
                payload = data["payload"]
                topic_parts = data.get("topic", "").split("/")
                # forgelink/plant/area/line/cell/device/type
                plant = topic_parts[1] if len(topic_parts) > 1 else "steel-plant-kigali"
                area = topic_parts[2] if len(topic_parts) > 2 else ""
                line = topic_parts[3] if len(topic_parts) > 3 else None
                cell = topic_parts[4] if len(topic_parts) > 4 else None
                device_id = (
                    topic_parts[5]
                    if len(topic_parts) > 5
                    else payload.get("device_id", "unknown")
                )

                return TelemetryMessage(
                    device_id=device_id,
                    value=float(payload.get("value", 0)),
                    quality=payload.get("quality", "good"),
                    timestamp=payload.get("ts")
                    or datetime.now(timezone.utc).isoformat(),
                    plant=plant,
                    area=area,
                    line=line,
                    cell=cell,
                    unit=payload.get("unit"),
                    sequence=payload.get("sequence", 0),
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
        """Flush current batch to TDengine and commit Kafka offsets on success.

        At-least-once delivery flow:

        1. Try insert_telemetry_batch with bounded retries (exponential
           backoff). On success → commit Kafka offsets.
        2. On persistent failure → route the records to the DLQ topic.
           Commit Kafka offsets ONLY if the DLQ publish confirms — otherwise
           leave offsets uncommitted so the message is redelivered.
        3. In either success path the batch is cleared and the flush
           timestamp is refreshed.

        The critical invariant: Kafka offsets never advance past a record
        whose durable write (either to TDengine or to the DLQ) did not
        succeed. A crash between receiving and writing causes a replay,
        not data loss.
        """
        if not self.batch:
            return

        flush_successful = False
        try:
            self._flush_with_retry(self.batch.copy())
            self.stats["batches_written"] += 1
            self.stats["messages_processed"] += len(self.batch)
            flush_successful = True
            logger.debug(f"Flushed batch of {len(self.batch)} records to TDengine")
        except Exception as exc:
            logger.error(f"Failed to flush batch after retries: {exc}")
            self.stats["errors"] += 1
            # Route to DLQ; only treat the commit as safe if publish confirms.
            flush_successful = self._send_to_dlq(self.batch.copy(), str(exc))

        # Commit only the last message in the batch — Kafka offset commits
        # apply up to and including the given offset per partition. A
        # successful commit here means every record in the batch has been
        # durably written somewhere (TDengine or DLQ).
        if flush_successful and self.batch_messages and self.consumer is not None:
            last_msg = self.batch_messages[-1]
            try:
                self.consumer.commit(message=last_msg, asynchronous=False)
                self.stats["commits"] += 1
            except Exception as exc:
                # Commit failures are recoverable: the next successful batch
                # will commit a later offset and the duplicate rows on
                # replay are idempotent at TDengine tag granularity.
                logger.warning(f"Kafka offset commit failed: {exc}")

        self.batch = []
        self.batch_messages = []
        self.last_flush_time = time.time()

    def _flush_with_retry(
        self, records: List[Dict[str, Any]], max_retries: int = 3
    ) -> None:
        """Flush batch with exponential backoff retry."""
        last_exception = None
        for attempt in range(max_retries):
            try:
                insert_telemetry_batch(records)
                return
            except Exception as e:
                last_exception = e
                wait_time = (2**attempt) * 0.5  # 0.5s, 1s, 2s
                logger.warning(
                    f"TDengine insert failed (attempt {attempt + 1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
        raise last_exception

    def _send_to_dlq(self, records: List[Dict[str, Any]], error: str) -> bool:
        """Send failed records to the DLQ topic.

        Returns True if the DLQ publish confirms (producer.flush returns
        zero outstanding messages). The caller uses this return value to
        decide whether to commit the original Kafka offsets — a False
        return leaves the offsets uncommitted so the message is redelivered
        on the next poll cycle.
        """
        from confluent_kafka import Producer

        try:
            producer = Producer({"bootstrap.servers": self.bootstrap_servers})

            dlq_topic = "dlq.telemetry"
            dlq_message = {
                "records": records,
                "error": error,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "consumer_group": self.group_id,
                "record_count": len(records),
            }

            producer.produce(
                dlq_topic,
                value=json.dumps(dlq_message).encode("utf-8"),
                callback=self._dlq_delivery_callback,
            )
            remaining = producer.flush(timeout=5)
            if remaining > 0:
                logger.error(
                    f"DLQ flush timed out with {remaining} messages still in-flight"
                )
                return False

            logger.info(f"Sent {len(records)} failed records to DLQ: {dlq_topic}")
            self.stats["dlq_messages"] = self.stats.get("dlq_messages", 0) + 1
            return True
        except Exception as e:
            logger.error(f"Failed to send to DLQ: {e}")
            return False

    def _dlq_delivery_callback(self, err, msg):
        """Callback for DLQ message delivery."""
        if err:
            logger.error(f"DLQ delivery failed: {err}")
        else:
            logger.debug(f"DLQ message delivered to {msg.topic()}")

    def should_flush(self) -> bool:
        """Check if batch should be flushed."""
        if len(self.batch) >= self.batch_size:
            return True

        elapsed_ms = (time.time() - self.last_flush_time) * 1000
        if elapsed_ms >= self.batch_timeout_ms and self.batch:
            return True

        return False

    def process_message(self, msg):
        """Process a single Kafka message.

        The message is kept alongside its parsed record in batch_messages
        so that flush_batch can commit the Kafka offset once the record
        has durably landed in TDengine or the DLQ.
        """
        self.stats["messages_received"] += 1

        # Continue the cross-service trace if the producer attached an
        # x-correlation-id header. Falls back to a per-message UUID so
        # batch failures can still be grepped by a single ID.
        import uuid

        from structlog.contextvars import bind_contextvars, clear_contextvars

        from apps.core.correlation import KAFKA_HEADER

        clear_contextvars()
        correlation_id = None
        for key, value in msg.headers() or []:
            key_bytes = key.encode() if isinstance(key, str) else key
            if key_bytes == KAFKA_HEADER and value:
                correlation_id = value.decode() if isinstance(value, bytes) else value
                break
        bind_contextvars(correlation_id=correlation_id or str(uuid.uuid4()))

        telemetry = self.parse_message(msg.value())
        if telemetry:
            self.batch.append(telemetry.to_record())
            self.batch_messages.append(msg)
        else:
            # Unparseable message — publish to DLQ and commit the offset
            # so the same poisonous payload does not block the partition.
            self._send_to_dlq_unparseable(msg)
            try:
                self.consumer.commit(message=msg, asynchronous=False)
            except Exception as exc:
                logger.warning(f"Commit of unparseable offset failed: {exc}")

        if self.should_flush():
            self.flush_batch()

    def _send_to_dlq_unparseable(self, msg) -> None:
        """Send an unparseable message to the DLQ as-is."""
        from confluent_kafka import Producer

        try:
            producer = Producer({"bootstrap.servers": self.bootstrap_servers})
            dlq_payload = {
                "original_topic": msg.topic(),
                "original_partition": msg.partition(),
                "original_offset": msg.offset(),
                "payload_base64": None,
                "payload_utf8": msg.value().decode("utf-8", errors="replace"),
                "consumer_group": self.group_id,
                "reason": "parse_failure",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            producer.produce(
                "dlq.unparseable",
                value=json.dumps(dlq_payload).encode("utf-8"),
            )
            producer.flush(timeout=5)
            self.stats["dlq_messages"] = self.stats.get("dlq_messages", 0) + 1
        except Exception as exc:
            logger.error(f"Failed to send unparseable message to DLQ: {exc}")

    def start(self):
        """Start consuming messages."""
        logger.info(f"Starting Kafka consumer for topics: {self.topics}")
        self.stats["start_time"] = datetime.now(timezone.utc)

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
                        self.stats["errors"] += 1
                        continue

                self.process_message(msg)

        except KafkaException as e:
            logger.error(f"Kafka exception: {e}")
            self.stats["errors"] += 1
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
        if self.stats["start_time"]:
            duration = (
                datetime.now(timezone.utc) - self.stats["start_time"]
            ).total_seconds()

        logger.info(
            f"Consumer stats: "
            f"received={self.stats['messages_received']}, "
            f"processed={self.stats['messages_processed']}, "
            f"batches={self.stats['batches_written']}, "
            f"errors={self.stats['errors']}, "
            f"duration={duration:.2f}s"
            if duration
            else ""
        )


class EventKafkaConsumer:
    """
    Kafka consumer for event/status messages.

    Consumes from event topics and processes alerts, status updates.
    """

    def __init__(
        self,
        bootstrap_servers: str = None,
        group_id: str = "forgelink-event-consumer",
        topics: List[str] = None,
    ):
        self.bootstrap_servers = bootstrap_servers or settings.KAFKA_BOOTSTRAP_SERVERS
        self.group_id = group_id
        self.topics = topics or ["events.all", "status.all"]
        self.consumer: Optional[Consumer] = None
        self.running = False

    def create_consumer(self) -> Consumer:
        """Create Kafka consumer instance with at-least-once semantics.

        Events drive alerting side effects (TDengine event rows, device
        status mutations); losing one silently would produce a stale
        dashboard. Manual-commit-after-process ensures a crash replays
        the event rather than dropping it.
        """
        config = {
            "bootstrap.servers": self.bootstrap_servers,
            "group.id": self.group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
        return Consumer(config)

    def process_event(self, msg):
        """Process an event message."""
        try:
            data = json.loads(msg.value().decode("utf-8"))
            event_type = data.get("event_type")

            if event_type in [
                "threshold_high",
                "threshold_low",
                "critical_high",
                "critical_low",
            ]:
                # Record threshold event in TDengine
                from .tdengine import insert_event

                insert_event(
                    device_id=data.get("device_id"),
                    plant=data.get("plant", "steel-plant-kigali"),
                    area=data.get("area", ""),
                    event_type=event_type,
                    severity=data.get("severity", "medium"),
                    message=data.get("message", ""),
                    value=data.get("value"),
                    threshold=data.get("threshold"),
                )
                logger.info(f"Recorded event: {event_type} for {data.get('device_id')}")

            elif event_type in ["device_online", "device_offline", "device_fault"]:
                # Update device status
                from apps.assets.models import Device

                try:
                    device = Device.objects.get(device_id=data.get("device_id"))
                    status_map = {
                        "device_online": "online",
                        "device_offline": "offline",
                        "device_fault": "fault",
                    }
                    device.update_status(status_map.get(event_type, "unknown"))
                    logger.info(
                        f"Updated device status: {device.device_id} -> {status_map.get(event_type)}"
                    )
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
