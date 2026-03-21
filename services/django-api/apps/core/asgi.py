"""
ASGI config for ForgeLink.

Integrates Django ASGI with Socket.IO for real-time notifications.
"""
import os

import socketio
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'apps.core.settings')

# Initialize Django ASGI application
django_asgi_app = get_asgi_application()

# Create Socket.IO server
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins=settings.SOCKETIO.get('CORS_ALLOWED_ORIGINS', '*'),
    ping_timeout=settings.SOCKETIO.get('PING_TIMEOUT', 60),
    ping_interval=settings.SOCKETIO.get('PING_INTERVAL', 25),
    logger=True,
    engineio_logger=False,
)

# Socket.IO namespaces
from apps.alerts.socketio import AlertNamespace, set_alert_namespace
alert_namespace = AlertNamespace('/alerts')
sio.register_namespace(alert_namespace)
set_alert_namespace(alert_namespace)

# Wrap Django ASGI app with Socket.IO
application = socketio.ASGIApp(sio, django_asgi_app)
