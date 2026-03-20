# ForgeLink MQTT Bridge

Bridges MQTT messages from EMQX to Kafka for the ForgeLink steel factory IoT platform.

## Overview

The MQTT Bridge:

- Subscribes to `forgelink/#` on EMQX
- Parses UNS topic hierarchy (ISA-95)
- Routes messages to appropriate Kafka topics
- Handles malformed messages via DLQ

## Topic Mapping

| MQTT Topic Pattern | Kafka Topic |
|-------------------|-------------|
| `forgelink/*/melt-shop/*/telemetry` | `telemetry.melt-shop` |
| `forgelink/*/continuous-casting/*/telemetry` | `telemetry.continuous-casting` |
| `forgelink/*/rolling-mill/*/telemetry` | `telemetry.rolling-mill` |
| `forgelink/*/finishing/*/telemetry` | `telemetry.finishing` |
| `forgelink/*/*/events` | `events.all` |
| `forgelink/*/*/status` | `status.all` |
| (unparseable) | `dlq.unparseable` |

## UNS Topic Structure

```
forgelink/<plant>/<area>/<line>/<cell>/<device_id>/<type>

Example:
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry
```

## Telemetry Payload Format

```json
{
  "device_id": "temp-sensor-001",
  "timestamp": "2026-03-20T19:00:00Z",
  "value": 1547.3,
  "unit": "celsius",
  "quality": "good",
  "sequence": 10482
}
```

## Environment Variables

```bash
# EMQX
EMQX_HOST=emqx
EMQX_PORT=1883
EMQX_MQTT_USERNAME=bridge
EMQX_MQTT_PASSWORD=

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
KAFKA_PARTITIONS=3

# Logging
LOG_LEVEL=INFO
```

## Metrics (Prometheus)

| Metric | Description |
|--------|-------------|
| `mqtt_messages_received_total` | Total MQTT messages received |
| `mqtt_messages_processed_total` | Successfully processed messages |
| `mqtt_parse_errors_total` | Messages that failed to parse |
| `kafka_publish_latency_seconds` | Time to publish to Kafka |
| `kafka_publish_errors_total` | Failed Kafka publishes |

## Local Development

```bash
cd services/mqtt-bridge
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m bridge
```

## Running Tests

```bash
pytest
```
