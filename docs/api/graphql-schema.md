# GraphQL Schema Reference

**Last updated:** 2026-04-22
**Generated from:** `services/django-api/apps/api/schema.py` and `services/django-api/apps/telemetry/schema.py`
**Endpoint:** `/graphql/` (Django integration hub)

This is the human-readable schema reference. The authoritative schema is the Graphene schema in source — regenerate this document from source when the schema changes. The GraphiQL interface is served at `/graphql/` in dev for interactive exploration.

The root `Query` composes three sub-queries via multiple inheritance: `TelemetryQuery` (time-series data), `AssetQuery` (ISA-95 hierarchy), and `AlertQuery` (alert rules, alerts, history). See `apps/api/schema.py:723-733`.

## Authentication

Every request to `/graphql/` must carry a JWT bearer token. The Django middleware (`apps/core/middleware.py`) resolves the token, loads the user's permissions, and attaches them to the request. GraphQL resolvers that perform mutations check `request.user.has_perm('<permission>')`. See [zero-trust.md § Permission-based RBAC](../architecture/zero-trust.md#permission-based-rbac--implemented) for the permission model.

## Telemetry queries

Sourced from `TelemetryQuery` in `apps/telemetry/schema.py:274-432`. Telemetry reads go through `TelemetryService`, which hits TDengine for time-series data and PostgreSQL for asset metadata.

### Enums

| Enum | Values |
|---|---|
| `TimeRangeEnum` | `LAST_HOUR`, `LAST_6_HOURS`, `LAST_24_HOURS`, `LAST_7_DAYS`, `LAST_30_DAYS` |
| `AggregationIntervalEnum` | `RAW`, `ONE_MINUTE`, `FIVE_MINUTES`, `FIFTEEN_MINUTES`, `ONE_HOUR`, `ONE_DAY` |
| `QualityEnum` | `GOOD`, `BAD`, `UNCERTAIN` |
| `AnomalyTypeEnum` | `HIGH`, `LOW` |

### Queries

| Query | Arguments | Returns |
|---|---|---|
| `deviceHistory` | `deviceId: String!`, `timeRange: TimeRangeEnum`, `startTime: DateTime`, `endTime: DateTime`, `interval: AggregationIntervalEnum`, `limit: Int = 10000` | `DeviceHistoryType` (device_id, count, data) |
| `deviceLatest` | `deviceId: String!` | `DeviceLatestType` (device_id, timestamp, value, quality, area, unit) |
| `deviceStatistics` | `deviceId: String!`, `period: String = "24h"` | `DeviceStatisticsType` (avg, min, max, stddev, count, first/last timestamp) |
| `deviceAnomalies` | `deviceId: String!`, `period: String = "24h"`, `stdThreshold: Float = 3.0` | `AnomalyDetectionType` (device_id, count, anomalies) |
| `latestValues` | `deviceIds: [String]`, `area: String` | `MultiDeviceLatestType` (count, data) |
| `compareDevices` | `deviceIds: [String]!`, `startTime: DateTime!`, `endTime: DateTime!`, `interval: String = "1h"` | `[DeviceComparisonType]` |
| `areaOverview` | `area: String!` | `AreaOverviewType` (area, total_devices, online, warning, fault, devices) |
| `plantDashboard` | *(none)* | `PlantDashboardType` (per-area status + plant totals) |

### Example — device history with aggregation

```graphql
query RecentTemperature($deviceId: String!) {
  deviceHistory(
    deviceId: $deviceId
    timeRange: LAST_24_HOURS
    interval: FIVE_MINUTES
  ) {
    deviceId
    count
    data {
      timestamp
      value
      quality
    }
  }
}
```

### Example — plant dashboard

```graphql
query PlantOverview {
  plantDashboard {
    timestamp
    meltShop { total online warning fault }
    continuousCasting { total online warning fault }
    rollingMill { total online warning fault }
    finishing { total online warning fault }
    totals { devices online warning fault }
  }
}
```

## Asset queries

Sourced from `AssetQuery` in `apps/api/schema.py:348-465`. Asset reads go against the PostgreSQL asset registry (Plant → Area → Line → Cell → Device).

### Object types

All asset types expose the ISA-95 fields plus computed counts. Full field lists are in `apps/api/schema.py` (one type per model): `PlantType`, `AreaType`, `LineType`, `CellType`, `DeviceTypeType`, `DeviceGraphQLType`.

Notable computed fields on `DeviceGraphQLType` (`apps/api/schema.py:196-223`):
- `fullPath` — dotted path through the ISA-95 hierarchy
- `unsTopic` — the canonical MQTT topic for this device (see [uns-topic-hierarchy.md](../architecture/uns-topic-hierarchy.md))
- `effectiveUnit` — device-level unit override, falling back to DeviceType default
- `areaCode`, `plantCode` — flattened access to ancestor codes

### Queries

| Query | Arguments | Returns |
|---|---|---|
| `plants` | `isActive: Boolean` | `[PlantType]` |
| `plant` | `code: String!` | `PlantType` |
| `areas` | `plantCode: String`, `isActive: Boolean` | `[AreaType]` |
| `area` | `id: UUID!` | `AreaType` |
| `lines` | `areaId: UUID`, `isActive: Boolean` | `[LineType]` |
| `line` | `id: UUID!` | `LineType` |
| `cells` | `lineId: UUID`, `isActive: Boolean` | `[CellType]` |
| `cell` | `id: UUID!` | `CellType` |
| `deviceTypes` | *(none)* | `[DeviceTypeType]` |
| `deviceType` | `code: String!` | `DeviceTypeType` |
| `devices` | `areaCode: String`, `deviceTypeCode: String`, `status: String`, `isActive: Boolean`, `limit: Int = 100` | `[DeviceGraphQLType]` |
| `device` | `deviceId: String!` | `DeviceGraphQLType` |

### Example — devices in an area with UNS topics

```graphql
query MeltShopDevices {
  devices(areaCode: "melt-shop", isActive: true, limit: 200) {
    deviceId
    name
    deviceTypeCode
    unsTopic
    status
    warningHigh
    criticalHigh
    effectiveUnit
  }
}
```

## Alert queries

Sourced from `AlertQuery` in `apps/api/schema.py:473-590`. Backed by the Django alerts app (`apps/alerts/`).

### Queries

| Query | Arguments | Returns |
|---|---|---|
| `alertRules` | `severity: String`, `isActive: Boolean` | `[AlertRuleType]` |
| `alertRule` | `id: UUID!` | `AlertRuleType` |
| `alerts` | `status: String`, `severity: String`, `deviceId: String`, `areaCode: String`, `limit: Int = 100` | `[AlertType]` |
| `alert` | `id: UUID!` | `AlertType` |
| `activeAlerts` | `severity: String`, `areaCode: String` | `[AlertType]` |
| `alertHistory` | `deviceId: String`, `area: String`, `severity: String`, `limit: Int = 100` | `[AlertHistoryType]` |
| `alertStats` | `areaCode: String` | `JSONString` (`{total, active, by_severity, by_status}`) |

### Example — active critical alerts for an area

```graphql
query ActiveCriticalAlerts($area: String!) {
  activeAlerts(severity: "CRITICAL", areaCode: $area) {
    id
    deviceId
    ruleName
    severity
    message
    value
    threshold
    triggeredAt
    durationSeconds
  }
}
```

## Mutations

Sourced from `Mutation` in `apps/api/schema.py:709-715`. Every mutation checks the user's permission set before executing.

| Mutation | Arguments | Required permission | Returns |
|---|---|---|---|
| `acknowledgeAlert` | `alertId: UUID!`, `user: String!` | `alerts.acknowledge` | `{success, alert, error}` |
| `resolveAlert` | `alertId: UUID!`, `user: String!`, `notes: String` | `alerts.resolve` | `{success, alert, error}` |
| `bulkAcknowledgeAlerts` | `alertIds: [UUID]!`, `user: String!` | `alerts.acknowledge` | `{success, acknowledgedCount, errors}` |
| `bulkResolveAlerts` | `alertIds: [UUID]!`, `user: String!` | `alerts.resolve` | `{success, resolvedCount, errors}` |

### Example — acknowledge an alert

```graphql
mutation Acknowledge($alertId: UUID!, $user: String!) {
  acknowledgeAlert(alertId: $alertId, user: $user) {
    success
    error
    alert {
      id
      status
      acknowledgedAt
      acknowledgedBy
    }
  }
}
```

## Root-level sentinel fields

Two static fields on the root Query are used for health and version sniffing:

- `hello: String` — returns `"Welcome to ForgeLink Steel Factory IoT"` (`apps/api/schema.py:732`).
- `version: String` — returns `"1.0.0"` (`apps/api/schema.py:733`).

These are intentionally unauthenticated and cheap — use them in smoke tests and deployment health probes.

## Regenerating this document

The Graphene schema is the authoritative source. To regenerate the SDL:

```bash
cd services/django-api
python manage.py graphql_schema --schema apps.api.schema.schema --out schema.graphql
```

This emits the canonical SDL. Any discrepancy between `schema.graphql` and this document means this document is stale — update it and commit.

---

## Related docs

- [ROADMAP.md](../../ROADMAP.md)
- [Architecture overview](../architecture/overview.md)
- [UNS topic hierarchy](../architecture/uns-topic-hierarchy.md) — `unsTopic` field semantics
- [TDengine schema](../architecture/tdengine-schema.md) — how telemetry reads resolve
- [Zero Trust architecture](../architecture/zero-trust.md) — authentication and permissions for this endpoint
