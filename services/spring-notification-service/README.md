# ForgeLink Alert Service

Alert rules engine for the ForgeLink steel factory IoT platform.

## Overview

The Alert Service processes telemetry data and triggers alerts based on configurable rules. It:

- Consumes telemetry from Kafka
- Evaluates alert rules in real-time
- Publishes triggered alerts to RabbitMQ
- Provides gRPC API for rule management

## Alert Severities

| Severity | Description | Example |
|----------|-------------|---------|
| `CRITICAL` | Immediate action required | EAF overheat, mold breakout risk |
| `HIGH` | Urgent attention needed | Cooling flow deviation, vibration spike |
| `MEDIUM` | Scheduled maintenance | Filter replacement, calibration due |
| `LOW` | Informational | Shift change, production milestone |

## Rule Types

| Type | Description |
|------|-------------|
| `THRESHOLD` | Value exceeds/falls below threshold |
| `RATE_OF_CHANGE` | Value changes too rapidly |
| `DEVIATION` | Value deviates from baseline |
| `PATTERN` | Sequence of conditions |

## Kafka Topics

**Consumed:**
- `telemetry.*` — All telemetry data

**Published (via RabbitMQ):**
- `alert.triggered` — When a rule fires

## gRPC Endpoints

| Service | Method | Description |
|---------|--------|-------------|
| AlertRuleService | CreateRule | Create new alert rule |
| AlertRuleService | UpdateRule | Update existing rule |
| AlertRuleService | DeleteRule | Delete rule |
| AlertRuleService | ListRules | List all rules |

## Environment Variables

```bash
# Database
ALERT_DB_HOST=postgres
ALERT_DB_PORT=5432
ALERT_DB_NAME=alerts
ALERT_DB_USER=alerts
ALERT_DB_PASSWORD=

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# RabbitMQ
RABBITMQ_HOST=rabbitmq
RABBITMQ_PORT=5672
RABBITMQ_USER=forgelink
RABBITMQ_PASSWORD=

# IDP (JWT validation)
ALERT_IDP_JWKS_URL=http://forgelink-idp:8080/auth/jwks
```

## Example Alert Rules

### EAF Temperature Critical
```json
{
  "name": "EAF Temperature Critical",
  "devicePattern": "temp-sensor-*",
  "areaFilter": "melt-shop",
  "ruleType": "THRESHOLD",
  "condition": "value > 1700",
  "severity": "CRITICAL",
  "message": "EAF temperature exceeds safe operating limit"
}
```

### Vibration Spike
```json
{
  "name": "Motor Vibration High",
  "devicePattern": "vibration-*",
  "ruleType": "THRESHOLD",
  "condition": "value > 4.5",
  "severity": "HIGH",
  "message": "Vibration exceeds acceptable threshold"
}
```
