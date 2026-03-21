"""ForgeLink Core Middleware"""

import logging
import time
from typing import Optional

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

import httpx
import jwt

logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware:
    """
    Validates JWT tokens from Spring IDP.
    Fetches JWKS from IDP and caches for 1 hour.
    """

    JWKS_CACHE_KEY = "idp:jwks"

    def __init__(self, get_response):
        self.get_response = get_response
        self._jwks = None
        self._jwks_client = None

    def __call__(self, request):
        # Skip auth for health checks and public endpoints
        if self._is_public_path(request.path):
            return self.get_response(request)

        # Extract token
        token = self._extract_token(request)
        if not token:
            return self.get_response(request)

        # Validate token
        try:
            payload = self._validate_token(token)
            request.jwt_payload = payload
            request.user_id = payload.get("sub")
            request.user_email = payload.get("email")
            request.plant_id = payload.get("plant_id")

            # Get role_code from JWT (IDP assigns role to user)
            role_code = payload.get("role")  # Single role code from IDP
            request.role_code = role_code

            # Resolve role_code → permissions from Django
            request.user_permissions = self._resolve_permissions(role_code)

        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return JsonResponse({"error": "Invalid token"}, status=401)

        return self.get_response(request)

    def _resolve_permissions(self, role_code: Optional[str]) -> set:
        """Resolve role_code to set of permission codes."""
        if not role_code:
            return set()

        try:
            from apps.core.models import Role

            return Role.get_permissions_for_role(role_code)
        except Exception as e:
            logger.warning(f"Failed to resolve permissions for role {role_code}: {e}")
            return set()

    def _is_public_path(self, path: str) -> bool:
        """Check if path is public (no auth required)."""
        public_paths = [
            "/health/",
            "/ready/",
            "/metrics",
            "/admin/login/",
        ]
        return any(path.startswith(p) for p in public_paths)

    def _extract_token(self, request) -> Optional[str]:
        """Extract JWT from Authorization header."""
        auth_header = request.META.get("HTTP_AUTHORIZATION", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return None

    def _validate_token(self, token: str) -> dict:
        """Validate JWT using JWKS from IDP."""
        jwks = self._get_jwks()

        # Get the key ID from the token header
        header = jwt.get_unverified_header(token)
        kid = header.get("kid")

        # Find the matching key
        key = None
        for jwk in jwks.get("keys", []):
            if jwk.get("kid") == kid:
                key = jwt.algorithms.RSAAlgorithm.from_jwk(jwk)
                break

        if not key:
            raise jwt.InvalidTokenError("No matching key found")

        # Validate and decode
        return jwt.decode(
            token, key, algorithms=["RS256"], options={"verify_aud": False}
        )

    def _get_jwks(self) -> dict:
        """Fetch JWKS from IDP with caching."""
        # Check cache
        jwks = cache.get(self.JWKS_CACHE_KEY)
        if jwks:
            return jwks

        # Fetch from IDP
        try:
            response = httpx.get(settings.IDP["JWKS_URL"], timeout=10.0)
            response.raise_for_status()
            jwks = response.json()

            # Cache for 1 hour
            cache.set(self.JWKS_CACHE_KEY, jwks, settings.IDP["JWKS_CACHE_TTL"])

            return jwks
        except Exception as e:
            logger.error(f"Failed to fetch JWKS: {e}")
            raise jwt.InvalidTokenError("Could not fetch JWKS")


class RateLimitMiddleware:
    """
    Rate limiting using Redis.
    60 req/min per user, 600 req/min per endpoint globally.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.user_limit = 60  # per minute
        self.endpoint_limit = 600  # per minute

    def __call__(self, request):
        # Skip rate limiting for health checks
        if request.path in ["/health/", "/ready/"]:
            return self.get_response(request)

        # Get user identifier
        user_id = self._get_user_id(request)

        # Check user rate limit
        if user_id and not self._check_rate_limit(
            f"rate:user:{user_id}", self.user_limit
        ):
            return JsonResponse({"error": "Rate limit exceeded"}, status=429)

        # Check endpoint rate limit
        endpoint_key = f"rate:endpoint:{request.path}"
        if not self._check_rate_limit(endpoint_key, self.endpoint_limit):
            return JsonResponse({"error": "Endpoint rate limit exceeded"}, status=429)

        return self.get_response(request)

    def _get_user_id(self, request) -> Optional[str]:
        """Get user identifier from JWT or IP."""
        if hasattr(request, "jwt_payload"):
            return request.jwt_payload.get("sub")
        return request.META.get("REMOTE_ADDR")

    def _check_rate_limit(self, key: str, limit: int) -> bool:
        """Check and increment rate limit counter."""
        try:
            current = cache.get(key, 0)
            if current >= limit:
                return False

            # Increment with 60s TTL
            cache.set(key, current + 1, 60)
            return True
        except Exception as e:
            logger.warning(f"Rate limit check failed: {e}")
            return True  # Fail open


class AuditMiddleware:
    """
    Logs all write operations for audit trail.
    """

    WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only audit write operations
        if request.method not in self.WRITE_METHODS:
            return self.get_response(request)

        # Skip health checks
        if request.path in ["/health/", "/ready/"]:
            return self.get_response(request)

        start_time = time.time()
        response = self.get_response(request)
        duration = time.time() - start_time

        # Log audit entry asynchronously
        self._log_audit(request, response, duration)

        return response

    def _log_audit(self, request, response, duration: float):
        """Log audit entry."""
        try:
            from apps.audit.tasks import create_audit_log

            user_id = None
            if hasattr(request, "jwt_payload"):
                user_id = request.jwt_payload.get("sub")

            create_audit_log.delay(
                user_id=user_id,
                action=request.method,
                resource=request.path,
                ip_address=request.META.get("REMOTE_ADDR"),
                status_code=response.status_code,
                duration_ms=int(duration * 1000),
            )
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")
