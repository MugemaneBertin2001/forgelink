# ForgeLink Local Development Setup

## Prerequisites

- Docker Desktop (or Docker + Docker Compose)
- Git
- Python 3.12+ (for Django development)
- Java 21+ (for Spring development)
- Flutter 3.19+ (for mobile development)
- Node.js 20+ (optional, for tooling)

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/MugemaneBertin2001/forgelink.git
cd forgelink
```

### 2. Environment Setup

```bash
cp .env.example .env
# Edit .env with your local settings (defaults work for Docker)
```

### 3. Start Infrastructure

```bash
# Start all services
docker compose up -d

# Or start only infrastructure (for local service development)
docker compose up -d postgres redis tdengine kafka zookeeper rabbitmq emqx minio
```

### 4. Verify Services

```bash
# Check all containers are running
docker compose ps

# Check logs
docker compose logs -f forgelink-api
```

## Service URLs

| Service | URL |
|---------|-----|
| Django API | http://localhost:8000 |
| Django Admin | http://localhost:8000/admin |
| GraphQL | http://localhost:8000/graphql |
| Spring IDP | http://localhost:8080 |
| Spring Asset Service | http://localhost:8081 |
| Spring Alert Service | http://localhost:8082 |
| EMQX Dashboard | http://localhost:18083 |
| RabbitMQ Management | http://localhost:15672 |
| Kafka UI | http://localhost:8090 |
| Grafana | http://localhost:3000 |
| Jaeger | http://localhost:16686 |
| MinIO Console | http://localhost:9001 |
| Mailhog | http://localhost:8025 |

## Default Credentials

| Service | Username | Password |
|---------|----------|----------|
| Django Admin | admin@forgelink.local | Admin@ForgeLink2026! |
| EMQX | admin | forgelink_emqx_admin |
| RabbitMQ | forgelink | forgelink_rabbitmq_dev |
| Grafana | admin | forgelink_grafana_dev |
| MinIO | forgelink_minio | forgelink_minio_secret |

## Development Workflows

### Django Development

```bash
cd services/django-api
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run dev server (hot reload)
python manage.py runserver

# Run Celery worker
celery -A apps.core worker -l DEBUG
```

### Spring Development

```bash
cd services/spring-idp
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

### MQTT Testing

```bash
# Subscribe to all topics
docker exec -it forgelink-emqx emqx_ctl clients list

# Publish test message
mosquitto_pub -h localhost -p 1883 -u bridge -P bridge_dev_password \
  -t "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry" \
  -m '{"device_id":"temp-sensor-001","timestamp":"2026-03-20T10:00:00Z","value":1547.3,"unit":"celsius","quality":"good"}'
```

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs <service-name>

# Restart specific service
docker compose restart <service-name>

# Rebuild
docker compose build --no-cache <service-name>
```

### Database connection issues

```bash
# Check PostgreSQL
docker compose exec postgres psql -U postgres -c "\\l"

# Check TDengine
docker compose exec tdengine taos -s "SHOW DATABASES;"
```

### Reset everything

```bash
# Stop and remove containers, volumes
docker compose down -v

# Start fresh
docker compose up -d
```
