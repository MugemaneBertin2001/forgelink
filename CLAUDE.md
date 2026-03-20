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
| API Gateway | Django 5.1 | Integration hub, GraphQL |
| Domain Services | Spring Boot 3.3 | Headless microservices |
| Mobile | Flutter 3.19+ | Cross-platform |
| Identity | Spring IDP | RS256 JWT, JWKS |
| Secrets | HashiCorp Vault | Self-hosted |
| Object Storage | MinIO | Backups, AI models |
| Observability | Prometheus + Grafana + Loki + Jaeger | Full visibility |

---

## Naming Conventions

### Services
- `forgelink-api` — Django integration hub
- `forgelink-idp` — Identity provider
- `forgelink-asset-service` — Asset domain service
- `forgelink-alert-service` — Alert domain service
- `forgelink-mqtt-bridge` — MQTT to Kafka bridge

### Database Schemas (PostgreSQL)
- `forgelink` — Django relational data
- `idp` — Spring IDP users, tokens
- `assets` — Spring Asset Service
- `alerts` — Spring Alert Service

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
- `assets.changes` — Asset mutations
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

### Phase 1 — Foundation ✅ IN PROGRESS
- [x] CLAUDE.md
- [ ] README.md
- [ ] .gitignore
- [ ] .env.example
- [ ] docker-compose.yml
- [ ] docker-compose.override.yml
- [ ] Django API scaffold
- [ ] Spring IDP scaffold
- [ ] Spring Asset Service scaffold
- [ ] Spring Alert Service scaffold
- [ ] MQTT Bridge scaffold
- [ ] K8s base structure
- [ ] Docs structure
- [ ] scripts/setup-dev.sh
- [ ] Git init

### Phase 2 — Zero Trust Identity (pending)
### Phase 3 — UNS/MQTT Layer (pending)
### Phase 4 — Django API (pending)
### Phase 5 — Spring Boot Microservices (pending)
### Phase 6 — Flutter Mobile App (pending)
### Phase 7 — Kubernetes Deployment (pending)
### Phase 8 — CI/CD (pending)
### Phase 9 — Slack Bot (pending)

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

*Last updated: 2026-03-20 | Phase 1 in progress*
