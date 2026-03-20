"""ForgeLink RBAC Permission Classes"""
from rest_framework.permissions import BasePermission


class IsFactoryAdmin(BasePermission):
    """
    Permission check for FACTORY_ADMIN role.
    Full access to all operations.
    """
    message = "Factory admin access required."

    def has_permission(self, request, view):
        if not hasattr(request, 'user_roles'):
            return False
        return 'FACTORY_ADMIN' in request.user_roles


class IsPlantOperator(BasePermission):
    """
    Permission check for PLANT_OPERATOR or higher.
    Read all, write alerts/commands.
    """
    message = "Plant operator access required."

    ALLOWED_ROLES = {'FACTORY_ADMIN', 'PLANT_OPERATOR'}

    def has_permission(self, request, view):
        if not hasattr(request, 'user_roles'):
            return False
        return bool(set(request.user_roles) & self.ALLOWED_ROLES)


class IsTechnician(BasePermission):
    """
    Permission check for TECHNICIAN or higher.
    Read own area, acknowledge alerts.
    """
    message = "Technician access required."

    ALLOWED_ROLES = {'FACTORY_ADMIN', 'PLANT_OPERATOR', 'TECHNICIAN'}

    def has_permission(self, request, view):
        if not hasattr(request, 'user_roles'):
            return False
        return bool(set(request.user_roles) & self.ALLOWED_ROLES)


class IsViewer(BasePermission):
    """
    Permission check for VIEWER or higher.
    Read-only access.
    """
    message = "Viewer access required."

    ALLOWED_ROLES = {'FACTORY_ADMIN', 'PLANT_OPERATOR', 'TECHNICIAN', 'VIEWER'}

    def has_permission(self, request, view):
        if not hasattr(request, 'user_roles'):
            return False
        return bool(set(request.user_roles) & self.ALLOWED_ROLES)


class IsAuthenticated(BasePermission):
    """
    Check if user has valid JWT token.
    """
    message = "Authentication required."

    def has_permission(self, request, view):
        return hasattr(request, 'jwt_payload') and request.jwt_payload is not None


class CanWriteAlerts(BasePermission):
    """
    Permission for alert operations (acknowledge, resolve).
    Requires PLANT_OPERATOR or higher.
    """
    message = "Alert write access required."

    ALLOWED_ROLES = {'FACTORY_ADMIN', 'PLANT_OPERATOR'}

    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            # Read access for all authenticated users
            return hasattr(request, 'jwt_payload')

        if not hasattr(request, 'user_roles'):
            return False
        return bool(set(request.user_roles) & self.ALLOWED_ROLES)


class CanManageDevices(BasePermission):
    """
    Permission for device management.
    Read: all authenticated users
    Write: TECHNICIAN or higher
    """
    message = "Device management access required."

    WRITE_ROLES = {'FACTORY_ADMIN', 'PLANT_OPERATOR', 'TECHNICIAN'}

    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return hasattr(request, 'jwt_payload')

        if not hasattr(request, 'user_roles'):
            return False
        return bool(set(request.user_roles) & self.WRITE_ROLES)


class CanManageUsers(BasePermission):
    """
    Permission for user management.
    Only FACTORY_ADMIN.
    """
    message = "User management access required."

    def has_permission(self, request, view):
        if not hasattr(request, 'user_roles'):
            return False
        return 'FACTORY_ADMIN' in request.user_roles


class PlantAccessPermission(BasePermission):
    """
    Check if user has access to a specific plant.
    Users can only access data from their assigned plant.
    """
    message = "Access to this plant is not allowed."

    def has_object_permission(self, request, view, obj):
        # Factory admins can access all plants
        if hasattr(request, 'user_roles') and 'FACTORY_ADMIN' in request.user_roles:
            return True

        # Check if object has plant_id attribute
        if not hasattr(obj, 'plant_id'):
            return True

        # Check if user's plant matches object's plant
        user_plant = getattr(request, 'plant_id', None)
        return user_plant is None or obj.plant_id == user_plant
