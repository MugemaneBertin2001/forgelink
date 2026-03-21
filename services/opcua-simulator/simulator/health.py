"""Health check server for OPC-UA Simulator."""
import json
from aiohttp import web

# Global health status
health_status = {
    "opcua_running": False,
    "redis_connected": False,
    "nodes_count": 0,
    "last_update": None
}


async def handle_health(request):
    """Full health check with component details."""
    is_healthy = health_status["opcua_running"] and health_status["redis_connected"]

    return web.json_response(
        {
            "status": "healthy" if is_healthy else "unhealthy",
            "components": health_status
        },
        status=200 if is_healthy else 503
    )


async def handle_ready(request):
    """Readiness probe."""
    is_ready = health_status["opcua_running"]

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


def set_opcua_status(running: bool, nodes: int = 0):
    """Update OPC-UA server status."""
    health_status["opcua_running"] = running
    health_status["nodes_count"] = nodes


def set_redis_status(connected: bool):
    """Update Redis connection status."""
    health_status["redis_connected"] = connected


def set_last_update(timestamp: str):
    """Update last value update timestamp."""
    health_status["last_update"] = timestamp
