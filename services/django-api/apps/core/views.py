"""Core views including health checks."""

import logging

from django.db import connection
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def health_check(request):
    """Basic health check - always returns 200 if the app is running."""
    return JsonResponse({"status": "healthy", "service": "forgelink-api"})


def readiness_check(request):
    """
    Readiness check - verifies all dependencies are available.
    Returns 503 if any dependency is unavailable.
    """
    checks = {
        "database": False,
        "redis": False,
        "tdengine": False,
    }

    # Check PostgreSQL
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        checks["database"] = True
    except Exception as exc:
        logger.warning("readiness: postgres check failed: %s", exc)

    # Check Redis
    try:
        from django.core.cache import cache

        cache.set("health_check", "ok", 1)
        if cache.get("health_check") == "ok":
            checks["redis"] = True
    except Exception as exc:
        logger.warning("readiness: redis check failed: %s", exc)

    # Check TDengine. Historical bug: this imported a phantom
    # `get_tdengine_connection`, silently failing in the bare except and
    # making /ready/ always report 503 regardless of TDengine health. The
    # real client factory is apps.telemetry.tdengine.get_client().
    try:
        from apps.telemetry.tdengine import get_client

        client = get_client()
        # Cheap round-trip against the running TDengine instance.
        client.execute("SELECT SERVER_VERSION()").close()
        checks["tdengine"] = True
    except Exception as exc:
        logger.warning("readiness: tdengine check failed: %s", exc)

    all_healthy = all(checks.values())
    status_code = 200 if all_healthy else 503

    return JsonResponse(
        {
            "status": "ready" if all_healthy else "not_ready",
            "service": "forgelink-api",
            "checks": checks,
        },
        status=status_code,
    )
