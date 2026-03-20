# ForgeLink Django API

Integration hub for the ForgeLink steel factory IoT platform.

## Overview

The Django API serves as the central integration point for all client applications. It provides:

- **GraphQL API** — Primary client-facing API
- **REST API** — Health checks, webhooks, Slack callbacks
- **Admin UI** — Unfold-based factory floor dashboard
- **Celery Workers** — Background task processing

## Apps

| App | Purpose |
|-----|---------|
| `core` | Settings, middleware, JWT validation, rate limiting |
| `assets` | Plant, Area, Line, Cell, Device models |
| `telemetry` | Kafka consumer → TDengine storage |
| `alerts` | Alert states, dispatch, RabbitMQ consumer |
| `ai` | Anomaly detection, predictive maintenance |
| `audit` | Immutable action log |
| `api` | GraphQL + REST endpoints |

## Environment Variables

See `.env.example` in the project root. Key variables:

```bash
DJANGO_SECRET_KEY        # Required in production
DJANGO_DEBUG             # Set to false in production
DJANGO_DB_*              # PostgreSQL connection
TDENGINE_*               # TDengine connection
REDIS_*                  # Redis connection
KAFKA_*                  # Kafka connection
```

## Local Development

```bash
# From project root
docker compose up -d postgres redis tdengine kafka

# Create virtual environment
cd services/django-api
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver

# Run Celery worker (separate terminal)
celery -A apps.core worker -l INFO
```

## Running Tests

```bash
# Run all tests
pytest

# With coverage
pytest --cov=apps --cov-report=html

# Specific app
pytest apps/assets/
```

## API Endpoints

### GraphQL
- `POST /graphql/` — GraphQL endpoint
- `GET /graphql/` — GraphiQL interface (dev only)

### REST
- `GET /health/` — Health check
- `GET /ready/` — Readiness check
- `POST /webhooks/slack/` — Slack event callbacks
- `GET /metrics/` — Prometheus metrics

### Admin
- `/admin/` — Django admin (Unfold UI)

## Kafka Topics Consumed

| Topic | Handler |
|-------|---------|
| `telemetry.*` | Writes to TDengine |
| `assets.changes` | Syncs asset cache |

## RabbitMQ Queues Consumed

| Queue | Handler |
|-------|---------|
| `alert.triggered` | Dispatches alerts |

## Celery Queues

| Queue | Workers | Tasks |
|-------|---------|-------|
| `default` | General | Miscellaneous |
| `telemetry` | Dedicated | Aggregation, downsampling |
| `alerts` | Dedicated | Slack, FCM, email dispatch |
| `ai` | Dedicated | Anomaly detection, predictions |
