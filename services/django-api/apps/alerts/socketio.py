"""
Socket.IO namespace for real-time alert notifications.

Flutter app connects to /alerts namespace to receive:
- New alerts
- Alert acknowledgements
- Alert resolutions
- Alert statistics updates

Authentication:
- Client must provide JWT token in auth dict on connect
- Token is validated using same JWKS as REST API
- Permissions are checked for subscribe/acknowledge actions
"""
import logging
from typing import Optional, Dict, Any, Set

import jwt
import socketio
from django.conf import settings
from django.core.cache import cache
import httpx

logger = logging.getLogger(__name__)


class SocketIOAuthenticator:
    """JWT authenticator for Socket.IO connections."""

    JWKS_CACHE_KEY = "idp:jwks"

    @classmethod
    def validate_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Validate JWT token and return payload."""
        try:
            jwks = cls._get_jwks()
            header = jwt.get_unverified_header(token)
            kid = header.get("kid")

            key = None
            for jwk in jwks.get("keys", []):
                if jwk.get("kid") == kid:
                    key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                    break

            if not key:
                logger.warning("No matching JWKS key found")
                return None

            payload = jwt.decode(
                token,
                key,
                algorithms=["RS256"],
                options={"verify_aud": False}
            )
            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Socket.IO auth: token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Socket.IO auth: invalid token - {e}")
            return None
        except Exception as e:
            logger.error(f"Socket.IO auth error: {e}")
            return None

    @classmethod
    def _get_jwks(cls) -> dict:
        """Fetch JWKS with caching."""
        jwks = cache.get(cls.JWKS_CACHE_KEY)
        if jwks:
            return jwks

        try:
            response = httpx.get(settings.IDP["JWKS_URL"], timeout=10.0)
            response.raise_for_status()
            jwks = response.json()
            cache.set(jwks, settings.IDP["JWKS_CACHE_TTL"])
            return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            return {"keys": []}

    @classmethod
    def get_user_permissions(cls, role_code: str) -> Set[str]:
        """Get permissions for a role code."""
        try:
            from apps.core.models import Role
            return Role.get_permissions_for_role(role_code)
        except Exception:
            return set()


class AlertNamespace(socketio.AsyncNamespace):
    """
    Socket.IO namespace for real-time alert notifications.

    Authentication:
        Client must provide JWT token in auth dict:
        socket.connect({auth: {token: 'Bearer xxx'}})

    Events emitted:
        alert:new - New alert triggered
        alert:acknowledged - Alert acknowledged
        alert:resolved - Alert resolved
        alert:stats - Alert statistics update
        auth:error - Authentication error
        auth:success - Authentication successful

    Events received:
        subscribe:area - Subscribe to alerts for specific area
        subscribe:all - Subscribe to all alerts
        unsubscribe - Unsubscribe from alerts
    """

    def __init__(self, namespace: str = '/alerts'):
        super().__init__(namespace)
        # Track sessions: sid -> {user_id, email, role, permissions, areas, all}
        self.sessions: Dict[str, Dict[str, Any]] = {}

    async def on_connect(self, sid: str, environ: dict, auth: Optional[dict] = None):
        """Handle client connection with JWT authentication."""
        logger.info(f"Client connecting to alerts namespace: {sid}")

        # Extract token from auth
        token = None
        if auth:
            token = auth.get('token', '')
            if token.startswith('Bearer '):
                token = token[7:]

        if not token:
            logger.warning(f"Socket.IO connection rejected: no token - {sid}")
            await self.emit('auth:error', {'message': 'Authentication required'}, to=sid)
            raise ConnectionRefusedError('Authentication required')

        # Validate token
        payload = SocketIOAuthenticator.validate_token(token)
        if not payload:
            logger.warning(f"Socket.IO connection rejected: invalid token - {sid}")
            await self.emit('auth:error', {'message': 'Invalid or expired token'}, to=sid)
            raise ConnectionRefusedError('Invalid token')

        # Get user info and permissions
        role_code = payload.get('role')
        permissions = SocketIOAuthenticator.get_user_permissions(role_code)

        # Check if user has alerts.view permission
        if 'alerts.view' not in permissions and role_code != 'FACTORY_ADMIN':
            logger.warning(f"Socket.IO connection rejected: no alerts.view permission - {sid}")
            await self.emit('auth:error', {'message': 'Permission denied'}, to=sid)
            raise ConnectionRefusedError('Permission denied')

        # Store session info
        self.sessions[sid] = {
            'user_id': payload.get('sub'),
            'email': payload.get('email'),
            'role': role_code,
            'permissions': permissions,
            'area': payload.get('area'),  # Area restriction from token
            'subscribed_areas': set(),
            'subscribed_all': False,
        }

        logger.info(f"Client authenticated: {sid} - {payload.get('email')} ({role_code})")

        # Send auth success and initial stats
        await self.emit('auth:success', {
            'user': payload.get('email'),
            'role': role_code,
            'permissions': list(permissions),
        }, to=sid)

        # Send current active alert count
        from .services import AlertService
        stats = AlertService.get_alert_stats(hours=1)
        await self.emit('alert:stats', stats, to=sid)

    async def on_disconnect(self, sid: str):
        """Handle client disconnection."""
        session = self.sessions.pop(sid, None)
        if session:
            logger.info(f"Client disconnected: {sid} - {session.get('email')}")
        else:
            logger.info(f"Client disconnected: {sid}")

    async def on_subscribe_area(self, sid: str, data: dict):
        """
        Subscribe to alerts for a specific area.

        Args:
            data: {'area': 'melt-shop'}
        """
        session = self.sessions.get(sid)
        if not session:
            await self.emit('error', {'message': 'Not authenticated'}, to=sid)
            return

        area = data.get('area')
        if not area:
            await self.emit('error', {'message': 'area required'}, to=sid)
            return

        # Check area access restriction
        user_area = session.get('area')
        if user_area and user_area != area:
            await self.emit('error', {'message': f'Access denied for area: {area}'}, to=sid)
            return

        session['subscribed_areas'].add(area)
        await self.enter_room(sid, f'area:{area}')
        logger.info(f"Client {session.get('email')} subscribed to area: {area}")
        await self.emit('subscribed', {'area': area}, to=sid)

    async def on_subscribe_all(self, sid: str):
        """Subscribe to all alerts. Requires no area restriction."""
        session = self.sessions.get(sid)
        if not session:
            await self.emit('error', {'message': 'Not authenticated'}, to=sid)
            return

        # Users with area restriction cannot subscribe to all
        if session.get('area'):
            await self.emit('error', {
                'message': 'Cannot subscribe to all - restricted to area'
            }, to=sid)
            return

        session['subscribed_all'] = True
        await self.enter_room(sid, 'all')
        logger.info(f"Client {session.get('email')} subscribed to all alerts")
        await self.emit('subscribed', {'all': True}, to=sid)

    async def on_unsubscribe(self, sid: str, data: dict):
        """Unsubscribe from alerts."""
        session = self.sessions.get(sid)
        if not session:
            return

        if data.get('all'):
            session['subscribed_all'] = False
            await self.leave_room(sid, 'all')
            logger.info(f"Client {session.get('email')} unsubscribed from all")
        elif area := data.get('area'):
            session['subscribed_areas'].discard(area)
            await self.leave_room(sid, f'area:{area}')
            logger.info(f"Client {session.get('email')} unsubscribed from area: {area}")

    async def on_acknowledge(self, sid: str, data: dict):
        """
        Acknowledge an alert via Socket.IO.
        Requires: alerts.acknowledge permission

        Args:
            data: {'alert_id': 'uuid'}
        """
        session = self.sessions.get(sid)
        if not session:
            await self.emit('error', {'message': 'Not authenticated'}, to=sid)
            return

        # Check permission
        permissions = session.get('permissions', set())
        if 'alerts.acknowledge' not in permissions and session.get('role') != 'FACTORY_ADMIN':
            await self.emit('error', {'message': 'Permission denied: alerts.acknowledge required'}, to=sid)
            return

        alert_id = data.get('alert_id')
        if not alert_id:
            await self.emit('error', {'message': 'alert_id required'}, to=sid)
            return

        from .services import AlertService

        user = session.get('email', 'unknown')
        alert = AlertService.acknowledge_alert(alert_id, user)

        if alert:
            await self.emit('alert:acknowledged', {
                'alert_id': str(alert.id),
                'acknowledged_by': user,
                'acknowledged_at': alert.acknowledged_at.isoformat(),
            }, to=sid)

            # Broadcast to all subscribers
            await self._broadcast_alert_update('alert:acknowledged', alert)
        else:
            await self.emit('error', {'message': 'Alert not found or not active'}, to=sid)

    async def _broadcast_alert_update(self, event: str, alert):
        """Broadcast alert update to relevant subscribers."""
        area = alert.device.cell.line.area.code

        payload = {
            'alert_id': str(alert.id),
            'device_id': alert.device.device_id,
            'severity': alert.severity,
            'status': alert.status,
            'message': alert.message,
            'area': area,
        }

        # Emit to area room
        await self.emit(event, payload, room=f'area:{area}')

        # Emit to 'all' room
        await self.emit(event, payload, room='all')


# Global reference for broadcasting from services
_alert_namespace: Optional[AlertNamespace] = None


def get_alert_namespace() -> Optional[AlertNamespace]:
    """Get the alert namespace instance."""
    global _alert_namespace
    return _alert_namespace


def set_alert_namespace(namespace: AlertNamespace):
    """Set the alert namespace instance."""
    global _alert_namespace
    _alert_namespace = namespace


async def broadcast_new_alert(alert_data: dict):
    """
    Broadcast new alert to connected clients.

    Called from AlertService when a new alert is created.
    """
    ns = get_alert_namespace()
    if ns is None:
        logger.warning("Alert namespace not initialized, cannot broadcast")
        return

    area = alert_data.get('area')

    # Emit to area room
    if area:
        await ns.emit('alert:new', alert_data, room=f'area:{area}')

    # Emit to 'all' room
    await ns.emit('alert:new', alert_data, room='all')

    logger.info(f"Broadcast new alert: {alert_data.get('alert_id')}")


async def broadcast_alert_resolved(alert_data: dict):
    """Broadcast alert resolution to connected clients."""
    ns = get_alert_namespace()
    if ns is None:
        return

    area = alert_data.get('area')

    if area:
        await ns.emit('alert:resolved', alert_data, room=f'area:{area}')
    await ns.emit('alert:resolved', alert_data, room='all')
