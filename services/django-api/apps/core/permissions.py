"""
ForgeLink Permission Classes for REST Framework.

Permission-based access control:
- Check specific permissions like 'alerts.acknowledge'
- Not role-based (roles are just groups of permissions)
"""

from rest_framework.permissions import BasePermission


class IsAuthenticated(BasePermission):
    """Check if user has valid JWT token."""

    message = "Authentication required."

    def has_permission(self, request, view):
        return (
            hasattr(request, "user") and request.user and request.user.is_authenticated
        )


class HasPermission(BasePermission):
    """
    Check if user has a specific permission.

    Usage (as class attribute):
        class MyView(APIView):
            permission_classes = [HasPermission]
            required_permission = 'alerts.acknowledge'

    Usage (as callable):
        class MyView(APIView):
            permission_classes = [HasPermission("alerts.acknowledge")]
    """

    message = "Permission denied."

    def __init__(self, permission_code: str = None):
        """Initialize with optional permission code."""
        self.permission_code = permission_code

    def __call__(self):
        # DRF's default ``get_permissions`` does
        # ``[p() for p in self.permission_classes]`` — which works for a
        # class (instantiates it) but crashes for an instance unless
        # the instance is callable. Making instances return themselves
        # lets us keep the ergonomic ``permission_classes =
        # [HasPermission("assets.view")]`` form on views that don't
        # override ``get_permissions`` (e.g. audit, simulator detail
        # endpoints) without losing the class-level form either.
        return self

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False

        # Use permission_code if provided, otherwise look at view attribute
        required = self.permission_code or getattr(view, "required_permission", None)
        if not required:
            return True

        return request.user.has_permission(required)


class HasAnyPermission(BasePermission):
    """
    Check if user has any of the specified permissions.

    Usage:
        class MyView(APIView):
            permission_classes = [HasAnyPermission]
            required_permissions = ['alerts.acknowledge', 'alerts.resolve']
    """

    message = "Permission denied."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_any_permission"):
            return False

        required = getattr(view, "required_permissions", [])
        if not required:
            return True

        return request.user.has_any_permission(*required)


class HasAllPermissions(BasePermission):
    """
    Check if user has all of the specified permissions.

    Usage:
        class MyView(APIView):
            permission_classes = [HasAllPermissions]
            required_permissions = ['alerts.view', 'alerts.acknowledge']
    """

    message = "Permission denied."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_any_permission"):
            return False

        required = getattr(view, "required_permissions", [])
        if not required:
            return True

        return request.user.has_all_permissions(*required)


# =============================================================================
# Common Permission Shortcuts
# =============================================================================


class CanViewAssets(BasePermission):
    """Permission to view assets."""

    message = "Assets view permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False
        return request.user.has_permission("assets.view")


class CanManageAssets(BasePermission):
    """Permission to create/update/delete assets."""

    message = "Assets management permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False

        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return request.user.has_permission("assets.view")
        elif request.method == "POST":
            return request.user.has_permission("assets.create")
        elif request.method in ["PUT", "PATCH"]:
            return request.user.has_permission("assets.update")
        elif request.method == "DELETE":
            return request.user.has_permission("assets.delete")

        return False


class CanViewAlerts(BasePermission):
    """Permission to view alerts."""

    message = "Alerts view permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False
        return request.user.has_permission("alerts.view")


class CanAcknowledgeAlerts(BasePermission):
    """Permission to acknowledge alerts."""

    message = "Alert acknowledgement permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False
        return request.user.has_permission("alerts.acknowledge")


class CanResolveAlerts(BasePermission):
    """Permission to resolve alerts."""

    message = "Alert resolution permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False
        return request.user.has_permission("alerts.resolve")


class CanManageAlertRules(BasePermission):
    """Permission to manage alert rules."""

    message = "Alert rule management permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False

        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return request.user.has_permission("alerts.view")
        elif request.method == "POST":
            return request.user.has_permission("alerts.create_rule")
        elif request.method in ["PUT", "PATCH"]:
            return request.user.has_permission("alerts.update_rule")
        elif request.method == "DELETE":
            return request.user.has_permission("alerts.delete_rule")

        return False


class CanViewTelemetry(BasePermission):
    """Permission to view telemetry data."""

    message = "Telemetry view permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False
        return request.user.has_permission("telemetry.view")


class CanExportTelemetry(BasePermission):
    """Permission to export telemetry data."""

    message = "Telemetry export permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False
        return request.user.has_permission("telemetry.export")


class CanControlSimulator(BasePermission):
    """Permission to control simulator."""

    message = "Simulator control permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False

        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return request.user.has_permission("simulator.view")

        return request.user.has_permission("simulator.control")


class CanManageUsers(BasePermission):
    """Permission to manage users."""

    message = "User management permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False
        return request.user.has_permission("admin.manage_users")


class CanManageRoles(BasePermission):
    """Permission to manage roles."""

    message = "Role management permission required."

    def has_permission(self, request, view):
        if not getattr(request.user, "is_authenticated", False):
            return False
        if not hasattr(request.user, "has_permission"):
            return False

        if request.method in ["GET", "HEAD", "OPTIONS"]:
            return request.user.has_permission("admin.view_roles")

        return request.user.has_permission("admin.manage_roles")


# =============================================================================
# Area-based Access Control
# =============================================================================


class AreaAccessPermission(BasePermission):
    """
    Check if user can access a specific area.

    Works with objects that have an area relationship.
    """

    message = "Access to this area is not allowed."

    def has_object_permission(self, request, view, obj):
        if not request.user:
            return False

        # Superusers can access all
        if request.user.is_superuser:
            return True

        # Get area code from object
        area_code = None
        if hasattr(obj, "area_code"):
            area_code = obj.area_code
        elif hasattr(obj, "area"):
            area_code = obj.area.code if hasattr(obj.area, "code") else obj.area
        elif hasattr(obj, "device"):
            # Traverse device -> cell -> line -> area
            try:
                area_code = obj.device.cell.line.area.code
            except AttributeError:
                pass

        if not area_code:
            return True

        return request.user.can_access_area(area_code)
