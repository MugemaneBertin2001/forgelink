# ForgeLink OPC-UA Simulation Server

Simulates OPC-UA endpoints for steel plant PLCs. Creates an address space that mirrors the ISA-95 equipment hierarchy and updates values in real-time based on Django simulation tasks.

## Architecture

```
Django Simulator App
       │
       │ Redis Pub/Sub (value updates)
       ▼
┌─────────────────────────────────────┐
│     OPC-UA Simulation Server        │
├─────────────────────────────────────┤
│  Address Space:                     │
│  Root/Objects/                      │
│    └─ SteelPlantKigali/            │
│        ├─ MeltShop/                │
│        │   ├─ EAF1/                │
│        │   │   ├─ ElectrodeA/      │
│        │   │   │   ├─ TempSensor001│
│        │   │   │   └─ Current001   │
│        ├─ ContinuousCasting/       │
│        ├─ RollingMill/             │
│        └─ Finishing/               │
└─────────────────────────────────────┘
       │
       │ OPC-UA (tcp://0.0.0.0:4840)
       ▼
   Edge Gateway
```

## Features

- **OPC-UA Server**: Full OPC-UA server using asyncua library
- **ISA-95 Hierarchy**: Address space mirrors plant structure
- **Redis Integration**: Receives value updates from Django via pub/sub
- **Real-time Updates**: Updates OPC-UA nodes with proper timestamps and quality codes
- **Health Checks**: HTTP endpoints for Kubernetes probes
- **Prometheus Metrics**: Exposes metrics for monitoring

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `OPCUA_ENDPOINT` | `opc.tcp://0.0.0.0:4840/forgelink/` | OPC-UA server endpoint |
| `OPCUA_SERVER_NAME` | `ForgeLink Steel Plant Simulator` | Server display name |
| `OPCUA_REDIS_URL` | `redis://localhost:6379/2` | Redis connection URL |
| `OPCUA_REDIS_CHANNEL` | `forgelink:opcua:values` | Redis pub/sub channel |
| `OPCUA_DJANGO_API_URL` | `http://localhost:8000` | Django API base URL |
| `OPCUA_LOG_LEVEL` | `INFO` | Logging level |
| `OPCUA_HEALTH_PORT` | `8081` | Health check HTTP port |
| `OPCUA_METRICS_PORT` | `9091` | Prometheus metrics port |

## Endpoints

| Port | Protocol | Description |
|------|----------|-------------|
| 4840 | OPC-UA TCP | OPC-UA server endpoint |
| 8081 | HTTP | Health checks (/health, /ready, /live) |
| 9091 | HTTP | Prometheus metrics |

## Running

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python -m simulator
```

### Docker

```bash
docker build -t forgelink/opcua-simulator .
docker run -p 4840:4840 -p 8081:8081 forgelink/opcua-simulator
```

### Docker Compose

The service is included in the main docker-compose.yml:

```bash
docker compose up opcua-simulator
```

## Connecting with OPC-UA Client

Use any OPC-UA client (e.g., UaExpert, Prosys OPC UA Client) to connect:

- Endpoint: `opc.tcp://localhost:4840/forgelink/`
- Security: None (development only)

Browse to `Root/Objects/SteelPlantKigali/` to see the device nodes.

## Value Update Format

The server subscribes to Redis channel `forgelink:opcua:values` for value updates:

```json
{
  "device_id": "uuid-string",
  "opc_node_id": "ns=2;s=steelplantkigali/meltshop/eaf1/electrodea/tempsensor001",
  "mqtt_topic": "forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry",
  "value": 1547.3,
  "quality": "good",
  "timestamp": "2024-03-20T14:30:00.123Z",
  "sequence": 10482,
  "unit": "celsius"
}
```
