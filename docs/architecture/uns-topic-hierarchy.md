# ForgeLink UNS Topic Hierarchy

## Overview

ForgeLink uses a **Unified Namespace (UNS)** based on the ISA-95 equipment hierarchy. All MQTT topics follow a consistent structure that maps directly to the physical steel plant layout.

## Topic Structure

```
forgelink/<plant>/<area>/<line>/<cell>/<device_id>/<message_type>
```

| Level | Description | Example |
|-------|-------------|---------|
| `forgelink` | Root namespace | `forgelink` |
| `<plant>` | Plant identifier | `steel-plant-kigali` |
| `<area>` | Production area | `melt-shop`, `continuous-casting`, `rolling-mill`, `finishing` |
| `<line>` | Production line | `eaf-1`, `caster-1`, `roughing` |
| `<cell>` | Equipment cell | `electrode-a`, `mold`, `stand-1` |
| `<device_id>` | Device identifier | `temp-sensor-001`, `vibration-002` |
| `<message_type>` | Message type | `telemetry`, `status`, `events`, `commands` |

## Message Types

### `telemetry` (QoS 0)
Real-time sensor readings. High frequency, fire-and-forget.

```json
{
  "device_id": "temp-sensor-001",
  "timestamp": "2026-03-20T14:30:00.123Z",
  "value": 1547.3,
  "unit": "celsius",
  "quality": "good",
  "sequence": 10482
}
```

### `status` (QoS 1)
Device health and connectivity status. Lower frequency, guaranteed delivery.

```json
{
  "device_id": "temp-sensor-001",
  "timestamp": "2026-03-20T14:30:00Z",
  "online": true,
  "last_value_at": "2026-03-20T14:29:55Z",
  "battery_level": null,
  "signal_strength": -45,
  "firmware_version": "2.1.0",
  "uptime_seconds": 864000
}
```

### `events` (QoS 1)
Discrete events like alarms, threshold breaches, state changes.

```json
{
  "device_id": "temp-sensor-001",
  "timestamp": "2026-03-20T14:30:00Z",
  "event_type": "THRESHOLD_EXCEEDED",
  "severity": "HIGH",
  "message": "Temperature exceeded 1600°C threshold",
  "value": 1605.2,
  "threshold": 1600.0,
  "acknowledged": false
}
```

### `commands` (QoS 2)
Control commands sent to devices. Exactly-once delivery.

```json
{
  "command_id": "cmd-123456",
  "timestamp": "2026-03-20T14:30:00Z",
  "command": "SET_THRESHOLD",
  "parameters": {
    "high_threshold": 1650.0,
    "low_threshold": 1500.0
  },
  "issued_by": "operator@forgelink.local",
  "expires_at": "2026-03-20T14:35:00Z"
}
```

## Steel Plant Topic Examples

### Melt Shop

```
# EAF Temperature Sensors
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-b/temp-sensor-002/telemetry
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-c/temp-sensor-003/telemetry

# EAF Electrode Current
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/current-sensor-001/telemetry

# LRF Sensors
forgelink/steel-plant-kigali/melt-shop/lrf-1/ladle/temp-sensor-010/telemetry
forgelink/steel-plant-kigali/melt-shop/lrf-1/alloy-bin/level-sensor-001/telemetry

# Off-Gas System
forgelink/steel-plant-kigali/melt-shop/offgas/main-duct/temp-sensor-020/telemetry
forgelink/steel-plant-kigali/melt-shop/offgas/main-duct/flow-meter-001/telemetry
```

### Continuous Casting

```
# Tundish
forgelink/steel-plant-kigali/continuous-casting/caster-1/tundish/temp-sensor-030/telemetry
forgelink/steel-plant-kigali/continuous-casting/caster-1/tundish/level-sensor-010/telemetry
forgelink/steel-plant-kigali/continuous-casting/caster-1/tundish/flow-meter-010/telemetry

# Mold
forgelink/steel-plant-kigali/continuous-casting/caster-1/mold/level-sensor-011/telemetry
forgelink/steel-plant-kigali/continuous-casting/caster-1/mold/temp-sensor-031/telemetry
forgelink/steel-plant-kigali/continuous-casting/caster-1/mold/oscillation-sensor-001/telemetry

# Secondary Cooling
forgelink/steel-plant-kigali/continuous-casting/caster-1/cooling-zone-1/flow-meter-020/telemetry
forgelink/steel-plant-kigali/continuous-casting/caster-1/cooling-zone-2/flow-meter-021/telemetry
```

### Rolling Mill

```
# Reheating Furnace
forgelink/steel-plant-kigali/rolling-mill/reheat-furnace/zone-1/temp-sensor-040/telemetry
forgelink/steel-plant-kigali/rolling-mill/reheat-furnace/zone-2/temp-sensor-041/telemetry
forgelink/steel-plant-kigali/rolling-mill/reheat-furnace/zone-3/temp-sensor-042/telemetry

# Rolling Stands
forgelink/steel-plant-kigali/rolling-mill/roughing/stand-1/roll-force-001/telemetry
forgelink/steel-plant-kigali/rolling-mill/roughing/stand-1/motor-001/vibration-001/telemetry
forgelink/steel-plant-kigali/rolling-mill/finishing/stand-6/roll-force-006/telemetry
forgelink/steel-plant-kigali/rolling-mill/finishing/stand-6/strip-temp-001/telemetry

# Cooling Bed
forgelink/steel-plant-kigali/rolling-mill/cooling-bed/section-1/temp-sensor-050/telemetry
```

### Finishing

```
# Inspection
forgelink/steel-plant-kigali/finishing/inspection/station-1/ultrasonic-001/telemetry
forgelink/steel-plant-kigali/finishing/inspection/station-1/eddy-current-001/telemetry

# Bundling
forgelink/steel-plant-kigali/finishing/bundling/machine-1/counter-001/telemetry
forgelink/steel-plant-kigali/finishing/bundling/machine-1/weight-scale-001/telemetry
```

## Kafka Topic Mapping

| MQTT Pattern | Kafka Topic |
|--------------|-------------|
| `forgelink/*/melt-shop/**/telemetry` | `telemetry.melt-shop` |
| `forgelink/*/continuous-casting/**/telemetry` | `telemetry.continuous-casting` |
| `forgelink/*/rolling-mill/**/telemetry` | `telemetry.rolling-mill` |
| `forgelink/*/finishing/**/telemetry` | `telemetry.finishing` |
| `forgelink/**/**/status` | `status.all` |
| `forgelink/**/**/events` | `events.all` |
| Unparseable messages | `dlq.unparseable` |

## Retention Policy

| Topic Type | EMQX Retain | Kafka Retention |
|------------|-------------|-----------------|
| telemetry | No | 7 days |
| status | Yes (last value) | 30 days |
| events | No | 90 days |
| commands | No | 7 days |

## Quality of Service (QoS)

| Message Type | QoS Level | Rationale |
|--------------|-----------|-----------|
| telemetry | 0 | High frequency, acceptable loss |
| status | 1 | Important but idempotent |
| events | 1 | Must be delivered |
| commands | 2 | Exactly-once critical |

## Topic Subscription Patterns

### Subscribe to all telemetry from an area
```
forgelink/steel-plant-kigali/melt-shop/+/+/+/telemetry
```

### Subscribe to all events
```
forgelink/+/+/+/+/+/events
```

### Subscribe to specific device
```
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/#
```

### Subscribe to all plant data
```
forgelink/steel-plant-kigali/#
```

## Best Practices

1. **Use lowercase** — All topic segments should be lowercase with hyphens
2. **Consistent naming** — Device IDs should follow `<type>-<number>` pattern
3. **Include timestamps** — All payloads must include ISO 8601 timestamps
4. **Sequence numbers** — Telemetry should include sequence numbers for gap detection
5. **Quality indicators** — Include data quality flags (good, bad, uncertain)
