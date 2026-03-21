# CLAUDE.md — ForgeLink Steel Factory IoT Platform

> Claude's persistent memory for this project. Update after every phase.

---

## Project Overview

**ForgeLink** — Production-grade, zero-trust Industrial IoT platform for steel manufacturing. Monitors and controls equipment across the entire steelmaking process — from electric arc furnaces to finished rolled products. Fully self-hosted on vanilla Kubernetes.

---

## Steel Manufacturing Domain

### Production Flow
```
Scrap Yard → Melt Shop → Continuous Casting → Rolling Mill → Finishing → Dispatch
```

### Factory Areas (ISA-95 Hierarchy)

**1. Melt Shop**
- Electric Arc Furnace (EAF) — melts scrap steel at 1,600°C+
- Ladle Refining Furnace (LRF) — secondary metallurgy, alloy additions
- Ladle Transfer Cars — transport molten steel
- Electrode systems — graphite electrodes for EAF
- Off-gas systems — fume extraction, heat recovery

**2. Continuous Casting**
- Tundish — intermediate vessel, steel flow control
- Mold — primary solidification, oscillating copper mold
- Strand guide — secondary cooling, bending/unbending
- Torch cutting — cuts billets/slabs to length
- Runout tables — billet/slab transport

**3. Rolling Mill**
- Reheating furnace — billets heated to 1,100-1,200°C
- Roughing stands — initial size reduction
- Intermediate stands — progressive rolling
- Finishing stands — final dimensions
- Cooling beds — controlled cooling
- Shears — cut to length

**4. Finishing**
- Straightening machines
- Inspection stations (ultrasonic, eddy current)
- Bundling/stacking machines
- Weighing stations
- Marking/tagging systems

### Critical Measurements

| Measurement | Equipment | Unit | Critical Range |
|-------------|-----------|------|----------------|
| Molten steel temp | EAF, LRF, Tundish | °C | 1,550-1,650 |
| Electrode current | EAF | kA | 30-80 |
| Casting speed | Continuous caster | m/min | 0.8-2.5 |
| Mold level | Mold | mm | ±3mm variance |
| Cooling water flow | Secondary cooling | L/min | Per zone |
| Roll force | Rolling stands | kN | Per pass schedule |
| Strip temperature | Finishing mill | °C | 850-1,050 |
| Vibration | Motors, gearboxes | mm/s RMS | <4.5 |

### Device Types (~68 devices)

| Device Type | Count | Locations |
|-------------|-------|-----------|
| Temperature sensors (thermocouple) | 20 | EAF, LRF, tundish, mold, furnaces |
| Pressure sensors | 8 | Hydraulics, cooling water, gas lines |
| Vibration sensors | 12 | Motors, gearboxes, fans |
| Flow meters | 8 | Cooling water, gas, hydraulics |
| Level sensors | 4 | Mold level, tundish level |
| PLCs | 6 | Area controllers |
| VFDs (Variable Frequency Drives) | 10 | Motors, pumps, fans |

---

## Stack Decisions

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Time-series DB | TDengine 3.x | Purpose-built for IoT, 1M+ writes/sec |
| Relational DB | PostgreSQL 16 | Single instance, schema isolation |
| Cache/Sessions | Redis 7 | Logical DB separation |
| Message Streaming | Kafka 7.x | High-throughput telemetry |
| Task Queue | RabbitMQ 3.13 | Commands, alerts |
| MQTT Broker | EMQX 5.x | MQTT 5.0, mTLS, ACL |
| API Gateway | Django 5.1 | Integration hub, GraphQL, owns all data |
| Notifications | Spring Boot 3.3 | Slack webhook service |
| Real-time | Socket.IO | In-app notifications to Flutter |
| Mobile | Flutter 3.19+ | Cross-platform |
| Identity | Spring IDP | RS256 JWT, JWKS |
| Secrets | HashiCorp Vault | Self-hosted |
| Object Storage | MinIO | Backups, AI models |
| Observability | Prometheus + Grafana + Loki + Jaeger | Full visibility |

---

## Simplified Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Django API (Source of Truth)                       │
│  - Assets (ISA-95 hierarchy)                                                │
│  - Alerts (rules, active, history)                                          │
│  - Telemetry ingestion                                                      │
│  - REST + GraphQL APIs                                                      │
│  - Socket.IO for real-time                                                  │
└─────────────┬───────────────────────────────────┬───────────────────────────┘
              │ Kafka: alerts.notifications       │ Socket.IO
              ▼                                   ▼
┌─────────────────────────┐          ┌─────────────────────────┐
│ Spring Notification Svc │          │      Flutter App        │
│  - Slack webhooks       │          │  - Real-time alerts     │
│  - Simple HTTP POST     │          │  - Dashboard            │
└─────────────────────────┘          └─────────────────────────┘
              │
              ▼
         Slack Channel
```

**Data Ownership:**
- Django owns ALL business data (assets, alerts, telemetry)
- Spring IDP owns only authentication data
- Spring Notification Service is stateless (consumes Kafka, posts to Slack)

---

## Naming Conventions

### Services
- `forgelink-api` — Django integration hub (owns all business data)
- `forgelink-idp` — Spring Identity provider (JWT/JWKS)
- `forgelink-notification-service` — Spring Slack notifications
- `forgelink-mqtt-bridge` — MQTT to Kafka bridge
- `opcua-simulator` — OPC-UA simulation server (simulates PLCs)
- `edge-gateway` — OPC-UA to MQTT bridge

### Database Schemas (PostgreSQL)
- `forgelink` — Django relational data (assets, alerts, simulator)
- `idp` — Spring IDP users, tokens

### Redis Logical DBs
- DB0 — Django sessions + rate limiting
- DB1 — Spring IDP token blacklist
- DB2 — Celery broker + result backend

### Kafka Topics
- `telemetry.melt-shop` — Melt shop telemetry
- `telemetry.continuous-casting` — Casting telemetry
- `telemetry.rolling-mill` — Rolling mill telemetry
- `telemetry.finishing` — Finishing area telemetry
- `events.all` — All device events
- `status.all` — Device status updates
- `alerts.notifications` — Alert events for Slack (Django → Spring)
- `dlq.unparseable` — Dead letter queue

### UNS Topic Hierarchy (ISA-95)
```
forgelink/steel-plant-kigali/<area>/<line>/<cell>/<device_id>/<type>

Examples:
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry
forgelink/steel-plant-kigali/continuous-casting/caster-1/mold/level-sensor-001/telemetry
forgelink/steel-plant-kigali/rolling-mill/finishing/stand-6/roll-force-001/telemetry
```

---

## Configuration Constants

### Versions
- Python: 3.12
- Java: 21 (LTS)
- Spring Boot: 3.3.x
- Django: 5.1
- Flutter: 3.19+

### TDengine Retention
- Raw: 30 days
- 1-min aggregates: 90 days
- 1-hour aggregates: 1 year
- 1-day aggregates: indefinite

### Rate Limits
- 60 req/min per user
- 600 req/min per endpoint globally
- Telemetry: 1,000 msg/sec (3 Kafka partitions/topic)

### Authentication
- JWT: RS256, 24h access, 30d refresh
- Password: min 12 chars, 1 upper, 1 number, 1 special
- Refresh tokens: Redis only

### Factory
- Plant: `steel-plant-kigali`
- Areas: Melt Shop, Continuous Casting, Rolling Mill, Finishing
- ~68 devices
- Timezone: Africa/Kigali (CAT, UTC+2)

### Alert Severity
- CRITICAL — Immediate action (EAF overheat, mold breakout risk)
- HIGH — Urgent attention (cooling flow deviation, vibration spike)
- MEDIUM — Scheduled maintenance (filter replacement, calibration)
- LOW — Informational (shift change, production milestone)

---

## Build Progress

### Phase 1 — Foundation ✅ COMPLETE
- [x] CLAUDE.md
- [x] README.md
- [x] .gitignore
- [x] .env.example
- [x] docker-compose.yml (15 services)
- [x] docker-compose.override.yml
- [x] Django API scaffold (6 apps)
- [x] Spring IDP scaffold
- [x] Spring Notification Service scaffold
- [x] MQTT Bridge scaffold
- [x] K8s base structure
- [x] Docs structure
- [x] scripts/setup-dev.sh
- [x] Git init

### Phase 2 — Zero Trust Identity ✅ COMPLETE
- [x] Spring IDP User model + repository
- [x] Spring IDP JWT service (RS256 signing)
- [x] Spring IDP auth controller (login, refresh, logout)
- [x] Spring IDP JWKS endpoint
- [x] Spring IDP Flyway migrations
- [x] Spring IDP seed admin user
- [x] Django JWT middleware (JWKS validation)
- [x] Django permission classes (RBAC)
- [x] Django decorators (@require_roles)
- [x] SPIFFE/SPIRE K8s manifests
- [x] IDP unit tests

### Phase 3 — UNS/MQTT Layer ✅ COMPLETE
- [x] EMQX configuration (emqx.conf)
- [x] EMQX ACL rules (area-based device permissions)
- [x] EMQX user initialization script
- [x] UNS topic hierarchy documentation
- [x] TDengine schema documentation
- [x] Django Simulator app (models, admin, API)
- [x] Device profiles (temperature, pressure, vibration, etc.)
- [x] Simulated PLCs and devices (~68 devices)
- [x] Simulation sessions management
- [x] Celery tasks for value updates
- [x] OPC-UA simulation server
- [x] Edge Gateway (OPC-UA → MQTT)
- [x] Kafka topic initialization script
- [x] Django Unfold admin integration

### Phase 4 — Django API ✅ COMPLETE
- [x] TDengine client and connection manager
- [x] Telemetry service layer (queries, inserts, aggregations)
- [x] Telemetry REST API (device history, latest, stats, anomalies)
- [x] GraphQL schema with Graphene (TelemetryQuery)
- [x] Celery tasks for TDengine aggregation (1m, 1h, 1d rollups)
- [x] Data retention cleanup tasks
- [x] Data quality monitoring tasks
- [x] Anomaly detection tasks
- [x] Asset models (Plant, Area, Line, Cell, Device, DeviceType)
- [x] Asset REST API with full CRUD
- [x] Asset Django Unfold admin
- [x] Kafka consumer for telemetry ingestion
- [x] Kafka consumer management command

### Phase 5 — Notifications & Real-time ✅ COMPLETE
- [x] Simplified architecture (Django owns all data)
- [x] Removed Spring Asset Service (duplicate)
- [x] Spring Notification Service (Slack webhooks)
- [x] Kafka consumer for alerts.notifications
- [x] Simple HTTP POST to Slack webhook (no SDK)
- [x] Alert models in Django (AlertRule, Alert, AlertHistory)
- [x] Alert service with threshold evaluation
- [x] Kafka producer for alert notifications
- [x] Socket.IO integration (python-socketio)
- [x] AlertNamespace for real-time notifications
- [x] Subscribe by area or all alerts
- [x] Broadcast new alerts, acknowledgements, resolutions
- [x] Permission-based RBAC (not role-based)
- [x] Permission and Role models in Django
- [x] Django Unfold admin for custom roles
- [x] JWT middleware resolves role_code → permissions
- [x] Permission classes for REST API
- [x] Permission decorators for function views
- [x] JWT authentication for Socket.IO
- [x] Area-based access control
- [x] seed_permissions management command

### Phase 6 — Flutter Mobile App ✅ COMPLETE
- [x] Project setup with Riverpod, Go Router, Dio
- [x] JWT authentication with secure storage
- [x] API client with auth interceptor and token refresh
- [x] Socket.IO integration for real-time alerts
- [x] Industrial theme (steel blue + forge orange)
- [x] Login screen with validation
- [x] Dashboard (welcome, alert summary, quick stats, area status)
- [x] Alerts screen (tabs: active/acknowledged/history, filters, actions)
- [x] Assets screen (ISA-95 hierarchy browser)
- [x] Telemetry screen (device selector, chart, statistics)
- [x] Settings screen (profile, permissions, connection status, logout)
- [x] Permission-based UI (hide features user can't access)
- [x] Real-time connection status indicator
- [x] Bottom navigation with role-based tabs

### Phase 7 — Kubernetes Deployment ✅ COMPLETE
- [x] Namespace and base Kustomization structure
- [x] ConfigMaps (forgelink-config, emqx-config)
- [x] Secrets templates (forgelink, idp, notification, postgresql, emqx)
- [x] PostgreSQL StatefulSet with init scripts
- [x] Redis Deployment
- [x] Kafka StatefulSet (KRaft mode, no Zookeeper)
- [x] TDengine StatefulSet with persistent volumes
- [x] EMQX StatefulSet with cluster discovery
- [x] ForgeLink API Deployment (with Celery worker, beat, Kafka consumer)
- [x] ForgeLink IDP Deployment
- [x] ForgeLink Notification Service Deployment
- [x] Services for all components
- [x] Ingress with TLS and WebSocket support
- [x] HPA for API, IDP, Celery workers, Kafka consumers
- [x] Environment overlays (dev, staging, production)
- [x] Kustomize patches for replica/resource scaling

### Phase 8 — CI/CD ✅ COMPLETE
- [x] CI workflow (Django tests, Spring tests, Flutter tests, lint)
- [x] Build workflow (Docker images for API, IDP, Notification)
- [x] Deploy workflow (Kustomize-based K8s deployment)
- [x] Release workflow (changelog, GitHub releases, APK artifacts)
- [x] Security scanning (Trivy, Bandit)
- [x] Dependabot configuration (Python, Gradle, Flutter, Docker, Actions)
- [x] Git-cliff changelog configuration
- [x] K8s manifest validation (kubeval)
- [x] Automatic rollback on deployment failure
- [x] Smoke tests post-deployment

---

## IDP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Email/password → JWT + refresh token |
| POST | `/auth/refresh` | Refresh token → new JWT |
| POST | `/auth/logout` | Revoke refresh token |
| GET | `/auth/jwks` | Public key (JWKS format) |
| GET | `/auth/validate` | Token introspection |

## Permission-Based RBAC

### Architecture
```
IDP (Spring)                    Django
┌─────────────────┐            ┌─────────────────────────┐
│ Users           │            │ Permissions (atomic)    │
│ - email         │            │ - alerts.view           │
│ - password      │            │ - alerts.acknowledge    │
│ - role_code ────┼───JWT───►  │ - assets.create         │
│   (string)      │            │ - telemetry.export      │
└─────────────────┘            │ - ...                   │
                               ├─────────────────────────┤
                               │ Roles (groups)          │
                               │ - FACTORY_ADMIN → all   │
                               │ - PLANT_OPERATOR → [...] │
                               │ - Custom roles...       │
                               └─────────────────────────┘
```

- **IDP stores**: Users + assigned role_code (just a string)
- **Django stores**: Permissions + Roles (role_code → permissions)
- **Admin can**: Create custom roles via Django admin

### System Permissions

| Module | Permission | Description |
|--------|------------|-------------|
| **Assets** | `assets.view` | View asset hierarchy |
| | `assets.create` | Create assets |
| | `assets.update` | Update assets |
| | `assets.delete` | Delete assets |
| | `assets.manage_maintenance` | Maintenance records |
| **Alerts** | `alerts.view` | View alerts |
| | `alerts.acknowledge` | Acknowledge alerts |
| | `alerts.resolve` | Resolve alerts |
| | `alerts.create_rule` | Create alert rules |
| | `alerts.update_rule` | Update alert rules |
| | `alerts.delete_rule` | Delete alert rules |
| **Telemetry** | `telemetry.view` | View telemetry |
| | `telemetry.view_raw` | View raw data |
| | `telemetry.export` | Export data |
| **Simulator** | `simulator.view` | View simulation |
| | `simulator.control` | Control simulation |
| | `simulator.inject_faults` | Inject faults |
| **Admin** | `admin.manage_users` | Manage users |
| | `admin.manage_roles` | Manage roles |
| | `admin.view_audit` | View audit logs |

### Default Roles

| Role | Permissions |
|------|-------------|
| `FACTORY_ADMIN` | All permissions (superuser) |
| `PLANT_OPERATOR` | assets.view, alerts.*, telemetry.view, simulator.view |
| `TECHNICIAN` | assets.view, alerts.view/acknowledge, telemetry.view |
| `VIEWER` | *.view only (read-only) |

### Seed Permissions
```bash
python manage.py seed_permissions
```

## Demo Users (seeded)

| Email | Password | Role |
|-------|----------|------|
| admin@forgelink.local | Admin@ForgeLink2026! | FACTORY_ADMIN |
| operator@forgelink.local | Admin@ForgeLink2026! | PLANT_OPERATOR |
| tech@forgelink.local | Admin@ForgeLink2026! | TECHNICIAN |
| viewer@forgelink.local | Admin@ForgeLink2026! | VIEWER |

---

## Simulation Stack

### Architecture
```
Django Simulator App (Control Plane)
       │
       │ Celery tasks publish to Redis
       ▼
┌─────────────────────────────────────┐
│     OPC-UA Simulation Server        │
│  (Simulates steel plant PLCs)       │
│  - Address space: ISA-95 hierarchy  │
│  - ~68 device nodes                 │
│  - Subscribes to Redis for updates  │
└─────────────────────────────────────┘
       │ OPC-UA Subscription
       ▼
┌─────────────────────────────────────┐
│          Edge Gateway               │
│  - Connects to OPC-UA server        │
│  - Subscribes to value changes      │
│  - Translates to UNS MQTT topics    │
│  - Publishes to EMQX                │
└─────────────────────────────────────┘
       │ MQTT Publish
       ▼
┌─────────────────────────────────────┐
│            EMQX Broker              │
└─────────────────────────────────────┘
       │
       ▼
    MQTT Bridge → Kafka → TDengine
```

### Simulation Controls
- **Django Admin**: Full device/PLC management with Unfold UI
- **REST API**: For Flutter app integration
- **Celery Beat**: Scheduled value updates
- **Fault Injection**: Stuck, drift, noise, spike, dead sensor faults

### Running Simulation
```bash
# Start simulation stack
docker compose --profile simulation up

# Seed devices
docker compose exec forgelink-api python manage.py seed_simulator

# Initialize Kafka topics
docker compose --profile init run kafka-init
```

---

## Constraints (Never Violate)

1. No secrets in git
2. mTLS everywhere between services
3. No hardcoded IPs — K8s DNS or env vars
4. No `latest` Docker tags
5. No synchronous AI in request path
6. Multi-stage builds, distroless/alpine final
7. Health probes required
8. Reversible DB migrations
9. No cross-service direct DB access
10. 70% test coverage minimum
11. Spring never calls Django
12. No cloud-provider-specific K8s resources
13. TDengine for telemetry only
14. TDengine writes always batched (500 records or 1s)

---

## Django API Endpoints

### Telemetry API (`/api/telemetry/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/data/device/{device_id}/history/` | Device historical data |
| GET | `/data/device/{device_id}/latest/` | Device latest value |
| GET | `/data/device/{device_id}/stats/` | Device statistics |
| GET | `/data/device/{device_id}/anomalies/` | Detect anomalies |
| GET | `/data/latest/` | Latest values for multiple devices |
| POST | `/data/record/` | Record telemetry batch |
| POST | `/data/compare/` | Compare multiple devices |
| GET | `/areas/{area}/overview/` | Area device overview |
| GET | `/areas/{area}/latest/` | Area latest values |
| GET | `/dashboard/` | Plant-wide dashboard |
| POST | `/events/` | Record telemetry event |
| POST | `/schema/init/` | Initialize TDengine schema |

### Assets API (`/api/assets/`)

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/plants/` | List/create plants |
| GET/PUT/DELETE | `/plants/{code}/` | Plant CRUD |
| GET | `/plants/{code}/hierarchy/` | Full plant hierarchy |
| GET | `/plants/{code}/devices/` | All devices in plant |
| GET/POST | `/areas/` | List/create areas |
| GET | `/areas/{id}/devices/` | Devices in area |
| GET | `/areas/{id}/status_summary/` | Area status summary |
| GET/POST | `/lines/` | List/create lines |
| GET/POST | `/cells/` | List/create cells |
| GET/POST | `/device-types/` | List/create device types |
| GET/POST | `/devices/` | List/create devices |
| GET/PUT/DELETE | `/devices/{device_id}/` | Device CRUD |
| PATCH | `/devices/{device_id}/update_status/` | Update device status |
| PATCH | `/devices/{device_id}/update_thresholds/` | Update thresholds |
| GET/POST | `/devices/{device_id}/maintenance/` | Maintenance records |
| GET | `/devices/by_area/` | Devices by area |
| POST | `/devices/search/` | Advanced device search |
| GET | `/devices/status_summary/` | Overall status summary |
| GET/POST | `/maintenance/` | Maintenance records |
| GET | `/dashboard/` | Asset dashboard |

### Alerts API (`/api/alerts/`)

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/rules/` | List/create alert rules |
| GET/PUT/DELETE | `/rules/{id}/` | Alert rule CRUD |
| POST | `/rules/{id}/activate/` | Activate rule |
| POST | `/rules/{id}/deactivate/` | Deactivate rule |
| GET/POST | `/alerts/` | List/create alerts |
| GET | `/alerts/active/` | Get active alerts |
| POST | `/alerts/{id}/acknowledge/` | Acknowledge alert |
| POST | `/alerts/{id}/resolve/` | Resolve alert |
| POST | `/alerts/acknowledge_bulk/` | Bulk acknowledge |
| POST | `/alerts/resolve_bulk/` | Bulk resolve |
| GET | `/history/` | Alert history (read-only) |
| GET | `/stats/` | Alert statistics |

### Simulator API (`/api/simulator/`)

| Method | Path | Description |
|--------|------|-------------|
| GET/POST | `/profiles/` | Device profiles |
| GET/POST | `/plcs/` | Simulated PLCs |
| POST | `/plcs/{id}/start/` | Start PLC |
| POST | `/plcs/{id}/stop/` | Stop PLC |
| GET/POST | `/devices/` | Simulated devices |
| POST | `/devices/{id}/inject_fault/` | Inject fault |
| POST | `/devices/{id}/clear_fault/` | Clear fault |
| GET/POST | `/sessions/` | Simulation sessions |
| POST | `/sessions/{id}/start/` | Start session |
| POST | `/sessions/{id}/stop/` | Stop session |
| GET | `/events/` | Simulation events |
| GET | `/dashboard/overview/` | Simulator dashboard |

### GraphQL (`/graphql/`)

Queries available:
- `deviceHistory` — Historical telemetry
- `deviceLatest` — Latest device value
- `deviceStatistics` — Device stats
- `deviceAnomalies` — Anomaly detection
- `latestValues` — Multiple device latest
- `compareDevices` — Device comparison
- `areaOverview` — Area overview
- `plantDashboard` — Plant dashboard

---

## Kafka Consumers

```bash
# Run telemetry consumer
python manage.py consume_telemetry

# Run event consumer
python manage.py consume_telemetry --type events

# Run both
python manage.py consume_telemetry --type both

# Custom options
python manage.py consume_telemetry --batch-size 1000 --batch-timeout 2000
```

---

## Socket.IO Real-time (Django)

### Connection
```javascript
// Flutter/Web client connects to:
const socket = io('http://localhost:8000', {
  path: '/socket.io',
  transports: ['websocket']
});

// Join alerts namespace
const alertsSocket = io('http://localhost:8000/alerts');
```

### Events (Client → Server)
| Event | Payload | Description |
|-------|---------|-------------|
| `subscribe:area` | `{area: 'melt-shop'}` | Subscribe to area alerts |
| `subscribe:all` | - | Subscribe to all alerts |
| `unsubscribe` | `{area: 'melt-shop'}` or `{all: true}` | Unsubscribe |
| `acknowledge` | `{alert_id: 'uuid', user: 'username'}` | Acknowledge via WS |

### Events (Server → Client)
| Event | Payload | Description |
|-------|---------|-------------|
| `alert:new` | Alert data | New alert triggered |
| `alert:acknowledged` | `{alert_id, acknowledged_by, acknowledged_at}` | Alert acknowledged |
| `alert:resolved` | `{alert_id, resolved_by, resolved_at}` | Alert resolved |
| `alert:stats` | Stats object | Statistics update |
| `subscribed` | `{area: '...'}` or `{all: true}` | Subscription confirmed |

---

## Slack Webhook (Spring Notification Service)

The notification service consumes `alerts.notifications` from Kafka and posts to Slack:

```bash
# Webhook URL format
https://hooks.slack.com/services/T.../B.../...

# Environment variable
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

Alert payload posted to Slack includes:
- Severity emoji (rotating_light, warning, etc.)
- Device ID and name
- Plant/Area location
- Value vs threshold
- Timestamp (Africa/Kigali timezone)
- Alert ID for tracking

---

*Last updated: 2026-03-21 | All phases complete*
