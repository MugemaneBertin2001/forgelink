# ForgeLink Edge Gateway

Bridges OPC-UA server to MQTT broker, translating industrial data to the Unified Namespace (UNS) structure.

## Architecture

```
┌─────────────────────────────────────┐
│        OPC-UA Server                │
│    (opcua-simulator or real PLC)    │
└──────────────┬──────────────────────┘
               │ OPC-UA Subscription
               ▼
┌─────────────────────────────────────┐
│          Edge Gateway               │
├─────────────────────────────────────┤
│  • OPC-UA Client (asyncua)         │
│  • Value change subscriptions       │
│  • Path → UNS topic translation    │
│  • Dead-band filtering             │
│  • Message buffering               │
│  • Quality code translation        │
└──────────────┬──────────────────────┘
               │ MQTT Publish
               ▼
┌─────────────────────────────────────┐
│            EMQX Broker              │
└─────────────────────────────────────┘
```

## Features

- **OPC-UA Subscription**: Subscribes to value changes on all device nodes
- **UNS Translation**: Converts OPC-UA paths to ISA-95 MQTT topics
- **Dead-band Filtering**: Reduces traffic by filtering small changes
- **Message Buffering**: Buffers messages during MQTT disconnect
- **Auto-reconnect**: Handles OPC-UA and MQTT reconnection automatically
- **Quality Translation**: Maps OPC-UA StatusCodes to quality strings
- **Health Checks**: HTTP endpoints for Kubernetes probes
- **Prometheus Metrics**: Exposes operational metrics

## Topic Translation

OPC-UA path:
```
SteelPlantKigali/MeltShop/EAF1/ElectrodeA/TempSensor001
```

Translates to MQTT topic:
```
forgelink/steel-plant-kigali/melt-shop/eaf-1/electrode-a/temp-sensor-001/telemetry
```

## Message Format

Published MQTT message:
```json
{
  "device_id": "temp-sensor-001",
  "timestamp": "2024-03-20T14:30:00.123Z",
  "value": 1547.3,
  "quality": "good",
  "sequence": 10482
}
```

## Configuration

Environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `EDGE_OPCUA_ENDPOINT` | `opc.tcp://localhost:4840/forgelink/` | OPC-UA server endpoint |
| `EDGE_OPCUA_NAMESPACE` | `urn:forgelink:steel-plant` | OPC-UA namespace URI |
| `EDGE_MQTT_HOST` | `localhost` | MQTT broker host |
| `EDGE_MQTT_PORT` | `1883` | MQTT broker port |
| `EDGE_MQTT_USERNAME` | `bridge` | MQTT username |
| `EDGE_MQTT_PASSWORD` | `bridge_dev_password` | MQTT password |
| `EDGE_SUBSCRIPTION_INTERVAL` | `1000` | Subscription interval (ms) |
| `EDGE_DEAD_BAND` | `0.0` | Dead-band filter threshold |
| `EDGE_BUFFER_SIZE` | `10000` | Max buffered messages |
| `EDGE_LOG_LEVEL` | `INFO` | Logging level |

## Endpoints

| Port | Protocol | Description |
|------|----------|-------------|
| 8082 | HTTP | Health checks (/health, /ready, /live) |
| 9092 | HTTP | Prometheus metrics |

## Running

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the gateway
python -m gateway
```

### Docker

```bash
docker build -t forgelink/edge-gateway .
docker run -e EDGE_OPCUA_ENDPOINT=opc.tcp://opcua-simulator:4840/forgelink/ \
           -e EDGE_MQTT_HOST=emqx \
           forgelink/edge-gateway
```

### Docker Compose

The service is included in the main docker-compose.yml:

```bash
docker compose up edge-gateway
```

## Data Flow

1. **Discovery**: On startup, gateway browses OPC-UA server for variable nodes
2. **Subscription**: Creates monitored items for all device nodes
3. **Notification**: OPC-UA server sends data change notifications
4. **Translation**: Gateway converts OPC-UA path to MQTT topic
5. **Filtering**: Dead-band filter applied (if configured)
6. **Publishing**: Message published to MQTT or buffered if disconnected
7. **Buffering**: On reconnect, buffered messages are flushed
