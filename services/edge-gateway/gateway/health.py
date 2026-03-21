"""Health check server for Edge Gateway."""
from aiohttp import web

# Global health status
health_status = {
    "opcua_connected": False,
    "mqtt_connected": False,
    "nodes_subscribed": 0,
    "buffer_size": 0,
    "last_message": None
}


async def handle_health(request):
    """Full health check with component details."""
    is_healthy = health_status["opcua_connected"] and health_status["mqtt_connected"]

    return web.json_response(
        {
            "status": "healthy" if is_healthy else "unhealthy",
            "components": health_status
        },
        status=200 if is_healthy else 503
    )


async def handle_ready(request):
    """Readiness probe."""
    is_ready = health_status["opcua_connected"] and health_status["mqtt_connected"]

    return web.json_response(
        {"status": "ready" if is_ready else "not ready"},
        status=200 if is_ready else 503
    )


async def handle_live(request):
    """Liveness probe."""
    return web.json_response({"status": "alive"})


async def start_health_server(port: int):
    """Start the health check HTTP server."""
    app = web.Application()
    app.router.add_get('/health', handle_health)
    app.router.add_get('/ready', handle_ready)
    app.router.add_get('/live', handle_live)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()


def set_opcua_status(connected: bool, nodes: int = 0):
    """Update OPC-UA connection status."""
    health_status["opcua_connected"] = connected
    health_status["nodes_subscribed"] = nodes


def set_mqtt_status(connected: bool):
    """Update MQTT connection status."""
    health_status["mqtt_connected"] = connected


def set_buffer_size(size: int):
    """Update buffer size."""
    health_status["buffer_size"] = size


def set_last_message(timestamp: str):
    """Update last message timestamp."""
    health_status["last_message"] = timestamp
