# ForgeLink

**Industrial IoT Platform for Steel Manufacturing**

ForgeLink is a production-grade, zero-trust IoT platform designed for steel factories. It monitors and controls equipment across the entire steelmaking process — from electric arc furnaces to finished rolled products.

---

## Features

- **Real-time Telemetry** — Sub-second data from 68+ sensors across the plant
- **Predictive Maintenance** — AI-powered anomaly detection and failure prediction
- **Alert Management** — Multi-channel notifications (mobile, Slack, email)
- **Asset Registry** — Complete equipment hierarchy following ISA-95
- **Mobile App** — Flutter-based cross-platform monitoring
- **Zero Trust Security** — mTLS, JWT, SPIFFE/SPIRE throughout

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                               │
│   Flutter Mobile App    Web Browser    Slack Bot             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│              DJANGO API — INTEGRATION HUB                    │
│  GraphQL · REST · Admin (Unfold) · Celery                    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│         SPRING BOOT — DOMAIN SERVICES                        │
│  Identity Provider · Asset Service · Alert Service           │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    MESSAGING                                 │
│  Kafka (telemetry) · RabbitMQ (commands) · Redis (cache)     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    MQTT / UNS                                │
│  EMQX Broker · ISA-95 Topic Hierarchy · MQTT→Kafka Bridge    │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  FIELD DEVICES                               │
│  PLCs · Sensors · Actuators · OPC-UA Adapters                │
└─────────────────────────────────────────────────────────────┘
```

---

## Steel Plant Coverage

| Area | Equipment | Key Measurements |
|------|-----------|------------------|
| **Melt Shop** | EAF, LRF, Ladle Cars | Steel temp, electrode current |
| **Continuous Casting** | Tundish, Mold, Strand Guide | Mold level, casting speed |
| **Rolling Mill** | Reheating Furnace, Stands | Roll force, strip temp |
| **Finishing** | Inspection, Bundling | Weight, dimensions |

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Make (optional)

### Local Development

```bash
# Clone the repository
git clone https://github.com/your-org/forgelink.git
cd forgelink

# Copy environment variables
cp .env.example .env

# Start all services
docker compose up -d

# Seed factory data
python scripts/seed-factory-data.py

# Access services
# Django API:     http://localhost:8000
# Django Admin:   http://localhost:8000/admin
# GraphQL:        http://localhost:8000/graphql
# Spring IDP:     http://localhost:8080
# EMQX Dashboard: http://localhost:18083
# Grafana:        http://localhost:3000
# RabbitMQ:       http://localhost:15672
```

---

## Project Structure

```
forgelink/
├── services/
│   ├── django-api/          # Integration hub
│   ├── spring-idp/          # Identity provider
│   ├── spring-asset-service/# Asset management
│   ├── spring-alert-service/# Alert rules engine
│   └── mqtt-bridge/         # MQTT → Kafka bridge
├── mobile/
│   └── flutter-app/         # Cross-platform mobile
├── slack-bot/               # Slack integration
├── k8s/                     # Kubernetes manifests
├── docs/                    # Documentation
└── scripts/                 # Dev utilities
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Time-series DB | TDengine 3.x |
| Relational DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Streaming | Kafka (Confluent) |
| Queue | RabbitMQ |
| MQTT Broker | EMQX 5.x |
| API | Django 5.1 + Graphene |
| Services | Spring Boot 3.3 |
| Mobile | Flutter 3.19+ |
| Observability | Prometheus, Grafana, Loki, Jaeger |

---

## Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [Local Development](docs/deployment/local-dev.md)
- [Kubernetes Deployment](docs/deployment/kubernetes.md)
- [TDengine Schema](docs/architecture/tdengine-schema.md)
- [UNS Topic Hierarchy](docs/architecture/uns-topic-hierarchy.md)
- [API Reference](docs/api/graphql-schema.md)

---

## License

Proprietary — All rights reserved.

---

*ForgeLink — Forging the link between steel and intelligence*
