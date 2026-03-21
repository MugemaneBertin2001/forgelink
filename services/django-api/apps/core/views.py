"""Core views including health checks."""

from django.db import connection
from django.http import JsonResponse


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
    except Exception:
        pass

    # Check Redis
    try:
        from django.core.cache import cache

        cache.set("health_check", "ok", 1)
        if cache.get("health_check") == "ok":
            checks["redis"] = True
    except Exception:
        pass

    # Check TDengine
    try:
        from apps.telemetry.tdengine import get_tdengine_connection

        conn = get_tdengine_connection()
        if conn:
            checks["tdengine"] = True
            conn.close()
    except Exception:
        pass

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
