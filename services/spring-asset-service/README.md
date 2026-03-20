# ForgeLink Asset Service

Steel plant asset management service for the ForgeLink IoT platform.

## Overview

Manages the ISA-95 asset hierarchy for the steel factory:

- **Plant** — Top-level facility (e.g., steel-plant-kigali)
- **Area** — Major production area (Melt Shop, Rolling Mill, etc.)
- **Line** — Production line within an area
- **Cell** — Equipment group within a line
- **Device** — Individual sensor/actuator/PLC

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/plants` | List all plants |
| GET | `/api/plants/{id}` | Get plant details |
| POST | `/api/plants` | Create plant |
| GET | `/api/areas` | List areas (with filters) |
| GET | `/api/devices` | List devices (with filters) |
| GET | `/api/devices/{id}` | Get device details |
| POST | `/api/devices` | Register new device |
| PUT | `/api/devices/{id}` | Update device |

## Kafka Topics

**Published:**
- `assets.changes` — Emitted on every create/update/delete

## Environment Variables

```bash
# Database
ASSET_DB_HOST=postgres
ASSET_DB_PORT=5432
ASSET_DB_NAME=assets
ASSET_DB_USER=assets
ASSET_DB_PASSWORD=

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:9092

# IDP (JWT validation)
ASSET_IDP_JWKS_URL=http://forgelink-idp:8080/auth/jwks
```

## Local Development

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=dev
```

## Device Types

| Type | Description |
|------|-------------|
| `TEMPERATURE_SENSOR` | Thermocouple, RTD |
| `PRESSURE_SENSOR` | Hydraulic, pneumatic |
| `VIBRATION_SENSOR` | Accelerometer |
| `FLOW_METER` | Water, gas flow |
| `LEVEL_SENSOR` | Mold level, tundish level |
| `PLC` | Programmable logic controller |
| `VFD` | Variable frequency drive |
