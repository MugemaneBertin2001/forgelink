"""ForgeLink JWT Authentication for REST Framework"""
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser


class JWTUser:
    """
    User object created from JWT payload.
    Compatible with Django's user interface.
    """

    def __init__(self, payload: dict):
        self.payload = payload
        self.id = payload.get("sub")
        self.username = payload.get("sub")
        self.email = payload.get("email", "")
        self.roles = payload.get("roles", [])
        self.plant_id = payload.get("plant_id")
        self.is_authenticated = True
        self.is_active = True
        self.is_staff = "FACTORY_ADMIN" in self.roles
        self.is_superuser = "FACTORY_ADMIN" in self.roles

    def has_role(self, role: str) -> bool:
        """Check if user has a specific role."""
        return role in self.roles

    def has_perm(self, perm: str, obj=None) -> bool:
        """Check permission based on role."""
        if self.is_superuser:
            return True

        # Map permissions to roles
        perm_role_map = {
            "view": ["VIEWER", "TECHNICIAN", "PLANT_OPERATOR", "FACTORY_ADMIN"],
            "add": ["TECHNICIAN", "PLANT_OPERATOR", "FACTORY_ADMIN"],
            "change": ["PLANT_OPERATOR", "FACTORY_ADMIN"],
            "delete": ["FACTORY_ADMIN"],
        }

        action = perm.split(".")[-1].split("_")[0]
        allowed_roles = perm_role_map.get(action, [])

        return any(role in allowed_roles for role in self.roles)

    def has_module_perms(self, app_label: str) -> bool:
        """Check if user has any permissions for the app."""
        return self.is_authenticated

    def __str__(self):
        return self.username or "anonymous"


class JWTAuthentication(BaseAuthentication):
    """
    REST Framework authentication class using JWT.
    Works with JWTAuthenticationMiddleware.
    """

    def authenticate(self, request):
        # Check if middleware already validated the token
        if hasattr(request, "jwt_payload"):
            user = JWTUser(request.jwt_payload)
            return (user, request.jwt_payload)

        return None

    def authenticate_header(self, request):
        return "Bearer"
