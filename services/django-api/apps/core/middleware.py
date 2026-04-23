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

            # Get role_codes from JWT. Spring IDP writes a JSON array under "roles"
            # (User -> Set<Role>, serialized as JSON list). The singular "role"
            # claim is accepted as a compatibility fallback — warns if used.
            role_codes = self._extract_role_codes(payload)
            request.role_codes = role_codes
            # role_code preserved for audit/back-compat: joined comma-separated,
            # or None if no roles. Downstream code should prefer role_codes.
            request.role_code = ",".join(sorted(role_codes)) if role_codes else None

            # Resolve role_codes → permissions from Django
            request.user_permissions = self._resolve_permissions(role_codes)

        except jwt.ExpiredSignatureError:
            return JsonResponse({"error": "Token expired"}, status=401)
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return JsonResponse({"error": "Invalid token"}, status=401)

        return self.get_response(request)

    @staticmethod
    def _extract_role_codes(payload: dict) -> list:
        """Extract role codes from JWT payload, normalising to a list.

        Preferred claim: ``roles`` (list of role codes, matching Spring IDP).
        Accepted fallback: ``role`` (single string) — logged as deprecated.
        """
        roles_claim = payload.get("roles")
        if roles_claim is not None:
            if isinstance(roles_claim, list):
                return [r for r in roles_claim if r]
            if isinstance(roles_claim, str):
                return [roles_claim] if roles_claim else []
            # Set, tuple, or other iterable
            try:
                return [r for r in roles_claim if r]
            except TypeError:
                logger.warning(
                    "JWT 'roles' claim has unexpected type %s; ignoring",
                    type(roles_claim).__name__,
                )
                return []

        # Compatibility fallback for the legacy singular "role" claim.
        role_claim = payload.get("role")
        if role_claim:
            logger.warning(
                "JWT carries legacy singular 'role' claim; issuer should emit "
                "'roles' as a JSON array"
            )
            return [role_claim]
        return []

    def _resolve_permissions(self, role_codes: list) -> set:
        """Resolve a list of role codes to the union of permission codes."""
        if not role_codes:
            return set()

        try:
            from apps.core.models import Role

            return Role.get_permissions_for_roles(role_codes)
        except Exception as e:
            logger.warning(
                f"Failed to resolve permissions for roles {role_codes}: {e}"
            )
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
    ACTION_MAP = {
        "POST": "create",
        "PUT": "update",
        "PATCH": "update",
        "DELETE": "delete",
    }

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Only audit write operations
        if request.method not in self.WRITE_METHODS:
            return self.get_response(request)

        # Skip health checks and metrics
        skip_paths = ["/health/", "/ready/", "/metrics"]
        if any(request.path.startswith(p) for p in skip_paths):
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
            role_code = None
            if hasattr(request, "jwt_payload"):
                user_id = request.jwt_payload.get("sub") or request.jwt_payload.get(
                    "email"
                )
                # Prefer the list already extracted by JWTAuthenticationMiddleware.
                # Fall back to re-extracting from the payload in case this
                # request came through a code path that bypassed the auth middleware.
                role_codes = getattr(
                    request,
                    "role_codes",
                    JWTAuthenticationMiddleware._extract_role_codes(
                        request.jwt_payload
                    ),
                )
                role_code = (
                    ",".join(sorted(role_codes)) if role_codes else None
                )

            # Extract resource type and ID from path
            resource_type, resource_id = self._parse_resource(request.path)

            # Map HTTP method to action
            action = self.ACTION_MAP.get(request.method, request.method.lower())

            # Check for special actions
            if "acknowledge" in request.path:
                action = "acknowledge"
            elif "resolve" in request.path:
                action = "resolve"

            create_audit_log.delay(
                user_id=user_id,
                role_code=role_code,
                action=action,
                resource=request.path,
                resource_type=resource_type,
                resource_id=resource_id,
                method=request.method,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get("HTTP_USER_AGENT", "")[:500],
                status_code=response.status_code,
                duration_ms=int(duration * 1000),
            )
        except Exception as e:
            logger.warning(f"Failed to create audit log: {e}")

    def _parse_resource(self, path: str) -> tuple:
        """Extract resource type and ID from request path."""
        parts = [p for p in path.strip("/").split("/") if p]

        # Expected format: api/<resource>/<id>/... or api/<resource>/...
        if len(parts) >= 2 and parts[0] == "api":
            resource_type = parts[1].title().rstrip("s")  # alerts -> Alert
            resource_id = parts[2] if len(parts) > 2 else None
            return resource_type, resource_id

        return None, None

    def _get_client_ip(self, request) -> str:
        """Get client IP, accounting for proxies."""
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            return x_forwarded_for.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR", "")
