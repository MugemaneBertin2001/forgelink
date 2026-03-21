"""
ForgeLink Permission Decorators.

Permission-based decorators for function-based views.
For class-based views, use permission_classes.
"""

from functools import wraps

from django.http import JsonResponse


def require_permission(permission_code: str):
    """
    Decorator to require a specific permission.

    Usage:
        @require_permission('alerts.acknowledge')
        def acknowledge_alert(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, "user") or not request.user:
                return JsonResponse({"error": "Authentication required"}, status=401)

            if not request.user.has_permission(permission_code):
                return JsonResponse(
                    {"error": f"Permission denied: {permission_code} required"},
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_any_permission(*permission_codes):
    """
    Decorator to require any of the specified permissions.

    Usage:
        @require_any_permission('alerts.acknowledge', 'alerts.resolve')
        def handle_alert(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, "user") or not request.user:
                return JsonResponse({"error": "Authentication required"}, status=401)

            if not request.user.has_any_permission(*permission_codes):
                return JsonResponse(
                    {"error": f"Permission denied: one of {permission_codes} required"},
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_all_permissions(*permission_codes):
    """
    Decorator to require all specified permissions.

    Usage:
        @require_all_permissions('alerts.view', 'telemetry.view')
        def dashboard(request):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, "user") or not request.user:
                return JsonResponse({"error": "Authentication required"}, status=401)

            if not request.user.has_all_permissions(*permission_codes):
                return JsonResponse(
                    {"error": f"Permission denied: all of {permission_codes} required"},
                    status=403,
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


def require_authenticated(view_func):
    """Decorator to require any authenticated user."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if (
            not hasattr(request, "user")
            or not request.user
            or not request.user.is_authenticated
        ):
            return JsonResponse({"error": "Authentication required"}, status=401)
        return view_func(request, *args, **kwargs)

    return wrapper


def require_area_access(area_param: str = "area_code"):
    """
    Decorator to check area-based access.

    Args:
        area_param: Name of the parameter containing area code

    Usage:
        @require_area_access('area')
        def area_view(request, area):
            ...
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not hasattr(request, "user") or not request.user:
                return JsonResponse({"error": "Authentication required"}, status=401)

            # Get area code from kwargs or request
            area_code = kwargs.get(area_param) or request.GET.get(area_param)

            if area_code and not request.user.can_access_area(area_code):
                return JsonResponse(
                    {"error": f"Access denied for area: {area_code}"}, status=403
                )

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator


# =============================================================================
# Convenience Shortcuts
# =============================================================================

# Assets
require_view_assets = require_permission("assets.view")
require_create_assets = require_permission("assets.create")
require_update_assets = require_permission("assets.update")
require_delete_assets = require_permission("assets.delete")

# Alerts
require_view_alerts = require_permission("alerts.view")
require_acknowledge_alerts = require_permission("alerts.acknowledge")
require_resolve_alerts = require_permission("alerts.resolve")
require_manage_alert_rules = require_any_permission(
    "alerts.create_rule", "alerts.update_rule", "alerts.delete_rule"
)

# Telemetry
require_view_telemetry = require_permission("telemetry.view")
require_export_telemetry = require_permission("telemetry.export")

# Simulator
require_view_simulator = require_permission("simulator.view")
require_control_simulator = require_permission("simulator.control")

# Admin
require_manage_users = require_permission("admin.manage_users")
require_manage_roles = require_permission("admin.manage_roles")
