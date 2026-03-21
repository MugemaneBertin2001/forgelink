"""Health check endpoint for MQTT Bridge."""
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import logging

logger = logging.getLogger(__name__)


class HealthStatus:
    """Tracks component health status."""

    def __init__(self):
        self.mqtt_connected = False
        self.kafka_connected = False
        self.last_message_at = None
        self.messages_processed = 0

    def is_healthy(self) -> bool:
        """Return True if all critical components are healthy."""
        return self.mqtt_connected and self.kafka_connected

    def to_dict(self) -> dict:
        """Return health status as dictionary."""
        return {
            "status": "healthy" if self.is_healthy() else "unhealthy",
            "components": {
                "mqtt": {
                    "connected": self.mqtt_connected,
                },
                "kafka": {
                    "connected": self.kafka_connected,
                },
            },
            "stats": {
                "last_message_at": self.last_message_at,
                "messages_processed": self.messages_processed,
            }
        }


# Global health status
health_status = HealthStatus()


class HealthHandler(BaseHTTPRequestHandler):
    """HTTP handler for health endpoints."""

    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

    def do_GET(self):
        """Handle GET requests."""
        if self.path == "/health":
            self._handle_health()
        elif self.path == "/ready":
            self._handle_ready()
        elif self.path == "/live":
            self._handle_live()
        else:
            self.send_error(404, "Not Found")

    def _handle_health(self):
        """Full health check with component details."""
        status = health_status.to_dict()
        code = 200 if health_status.is_healthy() else 503
        self._send_json(code, status)

    def _handle_ready(self):
        """Readiness probe - is the service ready to receive traffic?"""
        if health_status.is_healthy():
            self._send_json(200, {"status": "ready"})
        else:
            self._send_json(503, {"status": "not ready"})

    def _handle_live(self):
        """Liveness probe - is the service alive?"""
        self._send_json(200, {"status": "alive"})

    def _send_json(self, code: int, data: dict):
        """Send JSON response."""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def start_health_server(port: int = 8080):
    """Start the health check server in a background thread."""
    server = HTTPServer(("0.0.0.0", port), HealthHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    logger.info(f"Health server started on port {port}")
    return server
