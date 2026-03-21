# ForgeLink TDengine Schema

## Overview

TDengine is ForgeLink's time-series database for storing telemetry data from steel plant equipment. It's optimized for high-throughput writes and time-range queries.

## Database Configuration

```sql
CREATE DATABASE IF NOT EXISTS forgelink_telemetry
  KEEP 365           -- Keep data for 1 year max
  DURATION 10        -- 10-day data files
  BUFFER 256         -- 256MB write buffer
  WAL_LEVEL 1        -- Write-ahead log level
  CACHEMODEL 'last_row';  -- Cache last row for fast queries
```

## Supertables

### `telemetry` — Sensor Readings

Primary table for all sensor telemetry data.

```sql
CREATE STABLE telemetry (
  ts TIMESTAMP,           -- Measurement timestamp
  value DOUBLE,           -- Measurement value
  quality NCHAR(10),      -- Data quality: good, bad, uncertain
  sequence BIGINT         -- Sequence number for gap detection
) TAGS (
  device_id NCHAR(64),    -- Device identifier
  plant NCHAR(32),        -- Plant name
  area NCHAR(32),         -- Production area
  line NCHAR(32),         -- Production line
  cell NCHAR(32),         -- Equipment cell
  unit NCHAR(20),         -- Unit of measurement
  device_type NCHAR(32)   -- Device type for filtering
);
```

### `device_status` — Device Health

Tracks device connectivity and health.

```sql
CREATE STABLE device_status (
  ts TIMESTAMP,
  online BOOL,
  last_seen TIMESTAMP,
  error_code NCHAR(32),
  error_message NCHAR(256)
) TAGS (
  device_id NCHAR(64),
  plant NCHAR(32),
  area NCHAR(32)
);
```

### `events` — Discrete Events

Stores alarms, alerts, and state changes.

```sql
CREATE STABLE events (
  ts TIMESTAMP,
  event_type NCHAR(32),
  severity NCHAR(16),
  message NCHAR(512),
  value DOUBLE,
  threshold DOUBLE,
  acknowledged BOOL,
  acknowledged_by NCHAR(64),
  acknowledged_at TIMESTAMP
) TAGS (
  device_id NCHAR(64),
  plant NCHAR(32),
  area NCHAR(32)
);
```

## Child Table Naming Convention

Child tables are auto-created with names derived from the UNS topic path:

```
<plant>_<area>_<line>_<cell>_<device_id>
```

Example:
```sql
-- For device: forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001
-- Child table name: steel_plant_kigali_melt_shop_eaf_1_electrode_a_temp_sensor_001
```

## Retention Policy

| Data Type | Retention | Storage |
|-----------|-----------|---------|
| Raw telemetry | 30 days | `telemetry` |
| 1-minute aggregates | 90 days | `telemetry_1m` |
| 1-hour aggregates | 1 year | `telemetry_1h` |
| 1-day aggregates | Indefinite | `telemetry_1d` |
| Events | 1 year | `events` |
| Device status | 90 days | `device_status` |

## Continuous Aggregation

### 1-Minute Aggregates

```sql
CREATE STABLE telemetry_1m (
  ts TIMESTAMP,
  avg_value DOUBLE,
  min_value DOUBLE,
  max_value DOUBLE,
  count INT
) TAGS (
  device_id NCHAR(64),
  plant NCHAR(32),
  area NCHAR(32),
  unit NCHAR(20)
);

-- Continuous query (managed by Django Celery)
SELECT
  _wstart as ts,
  AVG(value) as avg_value,
  MIN(value) as min_value,
  MAX(value) as max_value,
  COUNT(*) as count
FROM telemetry
WHERE ts > NOW() - 2m
INTERVAL(1m)
SLIDING(1m);
```

### 1-Hour Aggregates

```sql
CREATE STABLE telemetry_1h (
  ts TIMESTAMP,
  avg_value DOUBLE,
  min_value DOUBLE,
  max_value DOUBLE,
  std_value DOUBLE,
  count INT
) TAGS (
  device_id NCHAR(64),
  plant NCHAR(32),
  area NCHAR(32),
  unit NCHAR(20)
);
```

### 1-Day Aggregates

```sql
CREATE STABLE telemetry_1d (
  ts TIMESTAMP,
  avg_value DOUBLE,
  min_value DOUBLE,
  max_value DOUBLE,
  std_value DOUBLE,
  count INT,
  uptime_percent DOUBLE
) TAGS (
  device_id NCHAR(64),
  plant NCHAR(32),
  area NCHAR(32),
  unit NCHAR(20)
);
```

## Common Queries

### Get Latest Value for a Device

```sql
SELECT LAST_ROW(ts, value, quality)
FROM telemetry
WHERE device_id = 'temp-sensor-001';
```

### Get Time Range Data

```sql
SELECT ts, value, quality
FROM telemetry
WHERE device_id = 'temp-sensor-001'
  AND ts >= '2026-03-20T00:00:00Z'
  AND ts <= '2026-03-20T23:59:59Z'
ORDER BY ts ASC;
```

### Get Aggregated Data (1-hour intervals)

```sql
SELECT
  _wstart as ts,
  AVG(value) as avg,
  MAX(value) as max,
  MIN(value) as min
FROM telemetry
WHERE device_id = 'temp-sensor-001'
  AND ts >= NOW() - 24h
INTERVAL(1h);
```

### Get All Devices in an Area

```sql
SELECT DISTINCT device_id, device_type, unit
FROM telemetry
WHERE area = 'melt-shop';
```

### Get Devices Above Threshold

```sql
SELECT device_id, LAST_ROW(value) as last_value
FROM telemetry
WHERE area = 'melt-shop'
  AND LAST_ROW(value) > 1600
GROUP BY device_id;
```

## Batch Insert Example

```python
# Python example using taospy
records = [
    {
        'device_id': 'temp-sensor-001',
        'plant': 'steel-plant-kigali',
        'area': 'melt-shop',
        'line': 'eaf-1',
        'cell': 'electrode-a',
        'unit': 'celsius',
        'device_type': 'temperature',
        'ts': '2026-03-20T14:30:00.123Z',
        'value': 1547.3,
        'quality': 'good',
        'sequence': 10482
    },
    # ... more records
]

# Batch insert (500 records or 1 second, whichever comes first)
insert_telemetry_batch(records)
```

## Performance Considerations

1. **Batch writes** — Always batch 500 records or 1 second of data
2. **Tag cardinality** — Keep unique tag combinations under 1M
3. **Query time ranges** — Use indexed `ts` column for filtering
4. **Aggregation** — Use pre-computed aggregates for dashboards
5. **Retention** — Let TDengine handle TTL, don't manually delete

## Indexes

TDengine automatically indexes:
- Timestamp (`ts`) — primary index
- Tags — for filtering by device, area, etc.

No additional indexes needed for typical queries.
