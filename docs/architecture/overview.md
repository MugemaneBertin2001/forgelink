# ForgeLink Architecture Overview

## Introduction

ForgeLink is a production-grade Industrial IoT platform designed for steel manufacturing facilities. This document provides a high-level overview of the system architecture.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                        CLIENTS                               │
│   Flutter Mobile App    Web Browser    Slack Bot             │
└──────────────────────────┬──────────────────────────────────┘
                           │ JWT Bearer token
┌──────────────────────────▼──────────────────────────────────┐
│              DJANGO API — INTEGRATION HUB                    │
│  GraphQL · REST · Admin (Unfold) · Celery                    │
│                                                              │
│  Apps: assets · telemetry · alerts · ai · audit · api       │
└──────────────────────────┬──────────────────────────────────┘
     Django calls Spring   │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│         SPRING BOOT — DOMAIN SERVICES                        │
│  IDP (Identity)  ·  Asset Service  ·  Alert Service          │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    MESSAGING                                 │
│  Kafka (telemetry)  ·  RabbitMQ (commands)  ·  Redis         │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    MQTT / UNS                                │
│  EMQX Broker  ·  ISA-95 Topics  ·  MQTT→Kafka Bridge         │
└──────────────────────────┬──────────────────────────────────┘
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  FIELD DEVICES                               │
│  PLCs · Sensors · Actuators · OPC-UA Adapters                │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow Rules

1. **Clients → Django only** — Never directly to Spring services
2. **Django → Spring** — REST/gRPC calls, Spring never calls Django
3. **Spring → Kafka/RabbitMQ** — Asynchronous event publishing
4. **Django consumes** — Kafka/RabbitMQ for real-time updates
5. **Graceful degradation** — Django uses cached data if Spring is down

## Technology Stack

| Layer | Technology |
|-------|------------|
| Time-series DB | TDengine 3.x |
| Relational DB | PostgreSQL 16 |
| Cache | Redis 7 |
| Streaming | Kafka (Confluent) |
| Queue | RabbitMQ |
| MQTT | EMQX 5.x |
| API | Django 5.1 + GraphQL |
| Services | Spring Boot 3.3 |
| Mobile | Flutter 3.19+ |

## Security Model

- **Zero Trust** — No implicit trust between components
- **mTLS** — All service-to-service communication
- **JWT (RS256)** — Client authentication via Spring IDP
- **RBAC** — Role-based access control
- **Default-deny** — Kubernetes network policies

## Steel Plant Coverage

| Area | Equipment |
|------|-----------|
| Melt Shop | EAF, LRF, Ladle Cars |
| Continuous Casting | Tundish, Mold, Strand Guide |
| Rolling Mill | Reheating Furnace, Stands |
| Finishing | Inspection, Bundling |

## Next Steps

- See [UNS Topic Hierarchy](uns-topic-hierarchy.md) for MQTT topic structure
- See [TDengine Schema](tdengine-schema.md) for telemetry storage
- See [Zero Trust](zero-trust.md) for security implementation
