# ForgeLink

![Version](https://img.shields.io/badge/version-v1.0.0-blue) ![License](https://img.shields.io/badge/license-Proprietary-red) ![Demo](https://img.shields.io/badge/demo-Coming%20Soon-yellow)

![Django](https://img.shields.io/badge/Django-5.1-092E20?logo=django&logoColor=white) ![Spring Boot](https://img.shields.io/badge/Spring%20Boot-3.3-6DB33F?logo=springboot&logoColor=white) ![Flutter](https://img.shields.io/badge/Flutter-3.24-02569B?logo=flutter&logoColor=white) ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white) ![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis&logoColor=white) ![Kafka](https://img.shields.io/badge/Kafka-KRaft-231F20?logo=apachekafka&logoColor=white) ![TDengine](https://img.shields.io/badge/TDengine-3.x-0076D6) ![EMQX](https://img.shields.io/badge/EMQX-MQTT%205.0-7B61FF)

![Kubernetes](https://img.shields.io/badge/Kubernetes-k3s-326CE5?logo=kubernetes&logoColor=white) ![ArgoCD](https://img.shields.io/badge/ArgoCD-GitOps-EF7B4D?logo=argo&logoColor=white) ![Terraform](https://img.shields.io/badge/Terraform-IaC-844FBA?logo=terraform&logoColor=white) ![Ansible](https://img.shields.io/badge/Ansible-Automation-EE0000?logo=ansible&logoColor=white) ![Docker](https://img.shields.io/badge/Docker-Multi--Arch-2496ED?logo=docker&logoColor=white) ![GitHub Actions](https://img.shields.io/badge/CI%2FCD-GitHub%20Actions-2088FF?logo=githubactions&logoColor=white)

**Industrial IoT Platform for Steel Manufacturing**

ForgeLink is a production-grade, zero-trust IoT platform designed for steel factories. It monitors and controls equipment across the entire steelmaking process — from electric arc furnaces to finished rolled products.

---

## Features

- **Real-time Telemetry** — Sub-second data from 44+ sensors (temperature, pressure, vibration, flow, level) plus 6 PLCs and 10 VFDs across the plant
- **Alert Management** — Multi-channel notifications (mobile push and Slack; email on roadmap)
- **Asset Registry** — Complete equipment hierarchy following ISA-95
- **Mobile App** — Flutter-based cross-platform monitoring
- **Zero Trust Security** — JWT (RS256) at the API edge, SPIFFE/SPIRE workload identity deployed, mTLS for service-to-service as target state. See [docs/architecture/zero-trust.md](docs/architecture/zero-trust.md) for scope.

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
git clone https://github.com/MugemaneBertin2001/forgelink.git
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

## Roadmap

- Predictive maintenance — AI-powered anomaly detection and failure prediction (in development)
- Oracle Cloud deployment with public live demo
- Raspberry Pi home lab cluster deployment
- TDengine community partnership integration

---

## Contact & Consulting

ForgeLink is developed and maintained by **Mugemane Bertin**, a Kigali-based IIoT engineer specializing in industrial data infrastructure. For consulting inquiries, integration partnerships, or deployment support — especially for AVEVA PI migration, TDengine architecture, and ISA-95 UNS implementation — reach out via [GitHub](https://github.com/MugemaneBertin2001) or [LinkedIn](https://linkedin.com/in/mugemane-bertin-15a383237).

---

## License

Proprietary — © 2026 Mugemane Bertin. All rights reserved. Viewing and evaluation permitted. Redistribution, modification, or commercial use without explicit written permission is prohibited.

---

*ForgeLink — Forging the link between steel and intelligence*
