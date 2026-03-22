"""Tests for core models."""

import pytest

from apps.core.models import DEFAULT_ROLES, SYSTEM_PERMISSIONS, Permission, Role


@pytest.mark.django_db
class TestPermissionModel:
    """Tests for Permission model."""

    def test_create_permission(self):
        """Test creating a permission."""
        permission = Permission.objects.create(
            code="test.create",
            name="Test Create",
            description="A test permission",
            module="assets",
        )
        assert permission.code == "test.create"
        assert permission.name == "Test Create"
        assert str(permission) == "test.create - Test Create"

    def test_permission_unique_code(self, permission):
        """Test that permission codes must be unique."""
        with pytest.raises(Exception):
            Permission.objects.create(
                code=permission.code,
                name="Duplicate",
                module="assets",
            )

    def test_permission_module_choices(self):
        """Test that module choices are valid."""
        valid_modules = [choice[0] for choice in Permission.MODULE_CHOICES]
        assert "assets" in valid_modules
        assert "alerts" in valid_modules
        assert "telemetry" in valid_modules

    def test_system_permissions_format(self):
        """Test that SYSTEM_PERMISSIONS follow the expected format."""
        for perm in SYSTEM_PERMISSIONS:
            assert len(perm) == 4
            code, name, module, description = perm
            assert "." in code
            assert len(name) > 0
            assert module in [c[0] for c in Permission.MODULE_CHOICES]


@pytest.mark.django_db
class TestRoleModel:
    """Tests for Role model."""

    def test_create_role(self, permission):
        """Test creating a role."""
        role = Role.objects.create(
            code="TEST_ROLE",
            name="Test Role",
            description="A test role",
        )
        role.permissions.add(permission)

        assert role.code == "TEST_ROLE"
        assert role.name == "Test Role"
        assert str(role) == "Test Role"
        assert permission in role.permissions.all()

    def test_get_permission_codes(self, role, permission):
        """Test getting permission codes from a role."""
        codes = role.get_permission_codes()
        assert permission.code in codes

    def test_get_permissions_for_role(self, role, permission, mock_cache):
        """Test getting permissions for a role with caching."""
        permissions = Role.get_permissions_for_role(role.code)
        assert permission.code in permissions

    def test_get_permissions_for_nonexistent_role(self, mock_cache):
        """Test getting permissions for a nonexistent role."""
        permissions = Role.get_permissions_for_role("NONEXISTENT")
        assert permissions == set()

    def test_get_permissions_for_inactive_role(self, role, mock_cache):
        """Test that inactive roles return no permissions."""
        role.is_active = False
        role.save()

        permissions = Role.get_permissions_for_role(role.code)
        assert permissions == set()

    def test_get_permissions_for_multiple_roles(self, db, mock_cache):
        """Test getting combined permissions from multiple roles."""
        # Create two roles with different permissions
        perm1 = Permission.objects.create(
            code="test.perm1", name="Perm 1", module="assets"
        )
        perm2 = Permission.objects.create(
            code="test.perm2", name="Perm 2", module="alerts"
        )

        role1 = Role.objects.create(code="ROLE1", name="Role 1")
        role1.permissions.add(perm1)

        role2 = Role.objects.create(code="ROLE2", name="Role 2")
        role2.permissions.add(perm2)

        combined = Role.get_permissions_for_roles(["ROLE1", "ROLE2"])
        assert "test.perm1" in combined
        assert "test.perm2" in combined

    def test_clear_permission_cache(self, role, mock_cache):
        """Test clearing permission cache."""
        Role.clear_permission_cache(role.code)
        mock_cache.delete.assert_called()

    def test_system_role_protection(self, db):
        """Test that system roles are marked correctly."""
        role = Role.objects.create(
            code="SYSTEM_ROLE",
            name="System Role",
            is_system=True,
        )
        assert role.is_system is True

    def test_default_roles_definition(self):
        """Test that DEFAULT_ROLES are properly defined."""
        assert "FACTORY_ADMIN" in DEFAULT_ROLES
        assert "PLANT_OPERATOR" in DEFAULT_ROLES
        assert "TECHNICIAN" in DEFAULT_ROLES
        assert "VIEWER" in DEFAULT_ROLES

        # Factory admin should have all permissions
        assert DEFAULT_ROLES["FACTORY_ADMIN"]["permissions"] == "*"

        # Other roles should have specific permissions
        assert isinstance(DEFAULT_ROLES["PLANT_OPERATOR"]["permissions"], list)
