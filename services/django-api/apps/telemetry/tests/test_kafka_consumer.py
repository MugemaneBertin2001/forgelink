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
