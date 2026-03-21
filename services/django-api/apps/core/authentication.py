"""ForgeLink JWT Authentication for REST Framework"""

from typing import Set

from rest_framework.authentication import BaseAuthentication


class JWTUser:
    """
    User object created from JWT payload.
    Compatible with Django's user interface.

    Permissions are resolved from role_code via Django's Role model.
    """

    def __init__(self, payload: dict, permissions: Set[str] = None):
        self.payload = payload
        self.id = payload.get("sub")
        self.username = payload.get("sub")
        self.email = payload.get("email", "")
        self.role_code = payload.get("role")  # Single role from IDP
        self.plant_id = payload.get("plant_id")
        self.area_code = payload.get("area")  # Optional area restriction
        self.is_authenticated = True
        self.is_active = True

        # Permissions resolved from Django Role model
        self._permissions = permissions or set()

        # Admin flags based on role
        self.is_staff = self.role_code == "FACTORY_ADMIN"
        self.is_superuser = self.role_code == "FACTORY_ADMIN"

    @property
    def permissions(self) -> Set[str]:
        """Get user's permission codes."""
        return self._permissions

    def has_permission(self, permission_code: str) -> bool:
        """
        Check if user has a specific permission.

        Args:
            permission_code: Permission code like 'alerts.acknowledge'
        """
        if self.is_superuser:
            return True
        return permission_code in self._permissions

    def has_any_permission(self, *permission_codes: str) -> bool:
        """Check if user has any of the specified permissions."""
        if self.is_superuser:
            return True
        return bool(set(permission_codes) & self._permissions)

    def has_all_permissions(self, *permission_codes: str) -> bool:
        """Check if user has all of the specified permissions."""
        if self.is_superuser:
            return True
        return set(permission_codes).issubset(self._permissions)

    def has_perm(self, perm: str, obj=None) -> bool:
        """Django-compatible permission check."""
        return self.has_permission(perm)

    def has_module_perms(self, app_label: str) -> bool:
        """Check if user has any permissions for the module."""
        if self.is_superuser:
            return True
        return any(p.startswith(f"{app_label}.") for p in self._permissions)

    def can_access_area(self, area_code: str) -> bool:
        """Check if user can access a specific area."""
        # Factory admin can access all
        if self.is_superuser:
            return True
        # If no area restriction, allow all
        if not self.area_code:
            return True
        # Check area match
        return self.area_code == area_code

    def __str__(self):
        return self.email or self.username or "anonymous"


class JWTAuthentication(BaseAuthentication):
    """
    REST Framework authentication class using JWT.
    Works with JWTAuthenticationMiddleware.
    """

    def authenticate(self, request):
        # Check if middleware already validated the token
        if hasattr(request, "jwt_payload"):
            # Get permissions resolved by middleware
            permissions = getattr(request, "user_permissions", set())
            user = JWTUser(request.jwt_payload, permissions)
            return (user, request.jwt_payload)

        return None

    def authenticate_header(self, request):
        return "Bearer"
