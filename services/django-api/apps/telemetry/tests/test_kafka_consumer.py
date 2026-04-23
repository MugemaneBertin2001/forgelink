"""Tests for Kafka consumer."""

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.telemetry.kafka_consumer import TelemetryKafkaConsumer, TelemetryMessage


class TestTelemetryMessage:
    """Tests for TelemetryMessage dataclass."""

    def test_to_record(self):
        """Test converting message to record format."""
        msg = TelemetryMessage(
            device_id="temp-001",
            value=1580.5,
            quality="good",
            timestamp="2024-01-01T00:00:00Z",
            plant="steel-plant-kigali",
            area="melt-shop",
            line="eaf-1",
            cell="electrode-a",
            unit="celsius",
            sequence=1,
        )

        record = msg.to_record()

        assert record["device_id"] == "temp-001"
        assert record["value"] == 1580.5
        assert record["quality"] == "good"
        assert record["plant"] == "steel-plant-kigali"

    def test_to_record_optional_fields(self):
        """Test record with optional fields as None."""
        msg = TelemetryMessage(
            device_id="temp-001",
            value=1580.5,
            quality="good",
            timestamp="2024-01-01T00:00:00Z",
            plant="steel-plant-kigali",
            area="melt-shop",
        )

        record = msg.to_record()

        assert record["line"] == ""
        assert record["cell"] == ""
        assert record["unit"] == ""


class TestTelemetryKafkaConsumer:
    """Tests for TelemetryKafkaConsumer."""

    @pytest.fixture
    def consumer(self):
        """Create test consumer."""
        with patch.object(TelemetryKafkaConsumer, "create_consumer"):
            consumer = TelemetryKafkaConsumer(
                bootstrap_servers="localhost:9092",
                batch_size=10,
                batch_timeout_ms=100,
            )
            return consumer

    def test_parse_message_direct_format(self, consumer):
        """Test parsing direct telemetry format."""
        msg_data = {
            "device_id": "temp-001",
            "value": 1580.5,
            "quality": "good",
            "ts": "2024-01-01T00:00:00Z",
            "plant": "steel-plant-kigali",
            "area": "melt-shop",
        }
        msg_value = json.dumps(msg_data).encode("utf-8")

        result = consumer.parse_message(msg_value)

        assert result is not None
        assert result.device_id == "temp-001"
        assert result.value == 1580.5
        assert result.quality == "good"

    def test_parse_message_uns_format(self, consumer):
        """Test parsing UNS payload format."""
        msg_data = {
            "topic": "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-001/telemetry",
            "payload": {
                "value": 1580.5,
                "quality": "good",
                "ts": "2024-01-01T00:00:00Z",
            },
        }
        msg_value = json.dumps(msg_data).encode("utf-8")

        result = consumer.parse_message(msg_value)

        assert result is not None
        assert result.device_id == "temp-001"
        assert result.plant == "steel-plant-kigali"
        assert result.area == "melt-shop"

    def test_parse_message_invalid_json(self, consumer):
        """Test parsing invalid JSON."""
        msg_value = b"not valid json"

        result = consumer.parse_message(msg_value)

        assert result is None

    def test_parse_message_missing_fields(self, consumer):
        """Test parsing message with missing required fields."""
        msg_data = {"some": "data"}
        msg_value = json.dumps(msg_data).encode("utf-8")

        result = consumer.parse_message(msg_value)

        assert result is None

    def test_should_flush_batch_size(self, consumer):
        """Test flush trigger by batch size."""
        consumer.batch = [{"data": i} for i in range(10)]

        assert consumer.should_flush() is True

    def test_should_flush_timeout(self, consumer):
        """Test flush trigger by timeout."""
        consumer.batch = [{"data": 1}]
        consumer.last_flush_time = 0  # Long time ago

        assert consumer.should_flush() is True

    def test_should_not_flush_empty(self, consumer):
        """Test no flush when batch is empty."""
        consumer.batch = []
        consumer.last_flush_time = 0

        assert consumer.should_flush() is False

    def test_flush_with_retry_success(self, consumer):
        """Test flush with successful retry."""
        records = [{"device_id": "test", "value": 1.0}]

        with patch(
            "apps.telemetry.kafka_consumer.insert_telemetry_batch"
        ) as mock_insert:
            mock_insert.return_value = None
            consumer._flush_with_retry(records)
            mock_insert.assert_called_once_with(records)

    def test_flush_with_retry_failure(self, consumer):
        """Test flush with retry exhaustion."""
        records = [{"device_id": "test", "value": 1.0}]

        with patch(
            "apps.telemetry.kafka_consumer.insert_telemetry_batch"
        ) as mock_insert:
            mock_insert.side_effect = Exception("Connection failed")

            with pytest.raises(Exception):
                consumer._flush_with_retry(records, max_retries=2)

            assert mock_insert.call_count == 2

    def test_send_to_dlq(self, consumer):
        """Test sending failed records to DLQ."""
        records = [{"device_id": "test", "value": 1.0}]

        with patch("confluent_kafka.Producer") as mock_producer_cls:
            mock_producer = MagicMock()
            mock_producer_cls.return_value = mock_producer

            consumer._send_to_dlq(records, "Test error")

            mock_producer.produce.assert_called_once()
            mock_producer.flush.assert_called_once()

    def test_statistics_tracking(self, consumer):
        """Test that statistics are tracked."""
        assert consumer.stats["messages_received"] == 0
        assert consumer.stats["messages_processed"] == 0
        assert consumer.stats["batches_written"] == 0
        assert consumer.stats["errors"] == 0

    def test_process_message_increments_stats(self, consumer):
        """Test that processing increments statistics."""
        msg = MagicMock()
        msg_data = {
            "device_id": "temp-001",
            "value": 1580.5,
            "quality": "good",
            "ts": "2024-01-01T00:00:00Z",
            "plant": "steel-plant-kigali",
            "area": "melt-shop",
        }
        msg.value.return_value = json.dumps(msg_data).encode("utf-8")

        with patch.object(consumer, "flush_batch"):
            consumer.process_message(msg)

        assert consumer.stats["messages_received"] == 1
        assert len(consumer.batch) == 1


class TestAtLeastOnceDelivery:
    """Pin the at-least-once delivery contract for the telemetry consumer.

    These tests guard against the historical regression where
    ``enable.auto.commit=True`` caused Kafka offsets to advance before the
    batch had landed in TDengine, silently losing data on any crash
    between poll and flush.
    """

    def _make_msg(self, offset=0, value=None):
        msg = MagicMock()
        msg.topic.return_value = "telemetry.melt-shop"
        msg.partition.return_value = 0
        msg.offset.return_value = offset
        msg.value.return_value = (
            value
            if value is not None
            else (
                b'{"device_id":"temp-001","value":1.0,"quality":"good",'
                b'"timestamp":"2024-01-01T00:00:00Z","plant":"p","area":"melt-shop"}'
            )
        )
        return msg

    def test_enable_auto_commit_is_false(self):
        consumer = TelemetryKafkaConsumer(bootstrap_servers="kafka:9092")
        with patch("apps.telemetry.kafka_consumer.Consumer") as mock_cls:
            consumer.create_consumer()
            config = mock_cls.call_args[0][0]
        assert (
            config["enable.auto.commit"] is False
        ), "at-least-once delivery requires manual commit after batch flush"

    def test_auto_offset_reset_is_earliest(self):
        consumer = TelemetryKafkaConsumer(bootstrap_servers="kafka:9092")
        with patch("apps.telemetry.kafka_consumer.Consumer") as mock_cls:
            consumer.create_consumer()
            config = mock_cls.call_args[0][0]
        assert config["auto.offset.reset"] == "earliest", (
            "new groups must backfill from the start so no historical "
            "telemetry is silently skipped on cold start"
        )

    @patch("apps.telemetry.kafka_consumer.insert_telemetry_batch")
    def test_successful_flush_commits_last_offset(self, mock_insert):
        mock_insert.return_value = 3
        consumer = TelemetryKafkaConsumer()
        consumer.consumer = MagicMock()

        msg1, msg2, msg3 = (
            self._make_msg(offset=10),
            self._make_msg(offset=11),
            self._make_msg(offset=12),
        )
        consumer.batch = [{"ts": "x", "value": i} for i in range(3)]
        consumer.batch_messages = [msg1, msg2, msg3]

        consumer.flush_batch()

        assert consumer.consumer.commit.called
        commit_kwargs = consumer.consumer.commit.call_args.kwargs
        assert commit_kwargs["message"] is msg3, (
            "per-partition commits are monotonic; the last message in the "
            "batch carries the highest offset"
        )
        assert commit_kwargs["asynchronous"] is False
        assert consumer.stats["commits"] == 1
        assert consumer.batch == [] and consumer.batch_messages == []

    @patch("apps.telemetry.kafka_consumer.insert_telemetry_batch")
    def test_no_commit_when_tdengine_and_dlq_both_fail(self, mock_insert):
        mock_insert.side_effect = RuntimeError("tdengine down")
        consumer = TelemetryKafkaConsumer()
        consumer.consumer = MagicMock()

        with patch.object(consumer, "_send_to_dlq", return_value=False):
            consumer.batch = [{"ts": "x", "value": 1.0}]
            consumer.batch_messages = [self._make_msg(offset=42)]
            consumer.flush_batch()

        assert consumer.consumer.commit.called is False, (
            "if neither the primary write nor the DLQ accepted the record, "
            "the Kafka offset MUST NOT advance — otherwise the record is "
            "silently lost on the next poll cycle"
        )
        assert consumer.stats["errors"] == 1

    @patch("apps.telemetry.kafka_consumer.insert_telemetry_batch")
    def test_commit_when_tdengine_fails_but_dlq_succeeds(self, mock_insert):
        mock_insert.side_effect = RuntimeError("tdengine down")
        consumer = TelemetryKafkaConsumer()
        consumer.consumer = MagicMock()
        msg = self._make_msg(offset=42)

        with patch.object(consumer, "_send_to_dlq", return_value=True):
            consumer.batch = [{"ts": "x", "value": 1.0}]
            consumer.batch_messages = [msg]
            consumer.flush_batch()

        assert consumer.consumer.commit.called is True
        assert consumer.consumer.commit.call_args.kwargs["message"] is msg

    def test_empty_batch_does_not_commit(self):
        consumer = TelemetryKafkaConsumer()
        consumer.consumer = MagicMock()
        consumer.batch = []
        consumer.batch_messages = []

        consumer.flush_batch()

        assert consumer.consumer.commit.called is False

    @patch("confluent_kafka.Producer")
    def test_unparseable_message_dlqed_and_committed(self, mock_producer_cls):
        mock_producer = MagicMock()
        mock_producer.flush.return_value = 0
        mock_producer_cls.return_value = mock_producer

        consumer = TelemetryKafkaConsumer()
        consumer.consumer = MagicMock()

        bad = self._make_msg(offset=99, value=b"totally not json")
        consumer.process_message(bad)

        # Published to dlq.unparseable and committed so the partition
        # is not blocked on the poisonous record.
        mock_producer.produce.assert_called()
        assert mock_producer.produce.call_args.args[0] == "dlq.unparseable"
        assert consumer.consumer.commit.called
        assert consumer.consumer.commit.call_args.kwargs["message"] is bad
