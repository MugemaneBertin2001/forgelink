"""Tests for permission classes."""

from unittest.mock import MagicMock

from rest_framework.test import APIRequestFactory

import pytest

from apps.core.permissions import (
    AreaAccessPermission,
    CanAcknowledgeAlerts,
    CanManageAssets,
    CanViewAlerts,
    CanViewAssets,
    HasAllPermissions,
    HasAnyPermission,
    HasPermission,
    IsAuthenticated,
)


@pytest.fixture
def api_request():
    """Create API request factory."""
    return APIRequestFactory()


@pytest.fixture
def mock_view():
    """Create a mock view."""
    view = MagicMock()
    return view


class TestIsAuthenticated:
    """Tests for IsAuthenticated permission."""

    def test_authenticated_user_allowed(self, api_request, mock_view):
        """Test that authenticated users are allowed."""
        request = api_request.get("/test/")
        request.user = MagicMock()
        request.user.is_authenticated = True

        permission = IsAuthenticated()
        assert permission.has_permission(request, mock_view) is True

    def test_unauthenticated_user_denied(self, api_request, mock_view):
        """Test that unauthenticated users are denied."""
        request = api_request.get("/test/")
        request.user = None

        permission = IsAuthenticated()
        result = permission.has_permission(request, mock_view)
        assert not result  # Could be False or None, both are falsy


class TestHasPermission:
    """Tests for HasPermission permission class."""

    def test_user_with_required_permission(self, api_request, mock_view, mock_user):
        """Test user with required permission is allowed."""
        mock_user.permissions = {"test.permission"}
        mock_view.required_permission = "test.permission"

        request = api_request.get("/test/")
        request.user = mock_user

        permission = HasPermission()
        assert permission.has_permission(request, mock_view) is True

    def test_user_without_required_permission(self, api_request, mock_view, mock_user):
        """Test user without required permission is denied."""
        mock_user.permissions = set()
        mock_view.required_permission = "test.permission"

        request = api_request.get("/test/")
        request.user = mock_user

        permission = HasPermission()
        assert permission.has_permission(request, mock_view) is False

    def test_no_required_permission(self, api_request, mock_view, mock_user):
        """Test that no required permission means allowed."""
        mock_view.required_permission = None

        request = api_request.get("/test/")
        request.user = mock_user

        permission = HasPermission()
        assert permission.has_permission(request, mock_view) is True


class TestHasAnyPermission:
    """Tests for HasAnyPermission permission class."""

    def test_user_with_one_of_permissions(self, api_request, mock_view, mock_user):
        """Test user with at least one permission is allowed."""
        mock_user.permissions = {"perm1"}
        mock_view.required_permissions = ["perm1", "perm2"]

        request = api_request.get("/test/")
        request.user = mock_user

        permission = HasAnyPermission()
        assert permission.has_permission(request, mock_view) is True

    def test_user_without_any_permission(self, api_request, mock_view, mock_user):
        """Test user without any required permission is denied."""
        mock_user.permissions = {"perm3"}
        mock_view.required_permissions = ["perm1", "perm2"]

        request = api_request.get("/test/")
        request.user = mock_user

        permission = HasAnyPermission()
        assert permission.has_permission(request, mock_view) is False


class TestHasAllPermissions:
    """Tests for HasAllPermissions permission class."""

    def test_user_with_all_permissions(self, api_request, mock_view, mock_user):
        """Test user with all required permissions is allowed."""
        mock_user.permissions = {"perm1", "perm2", "perm3"}
        mock_view.required_permissions = ["perm1", "perm2"]

        request = api_request.get("/test/")
        request.user = mock_user

        permission = HasAllPermissions()
        assert permission.has_permission(request, mock_view) is True

    def test_user_missing_permission(self, api_request, mock_view, mock_user):
        """Test user missing a required permission is denied."""
        mock_user.permissions = {"perm1"}
        mock_view.required_permissions = ["perm1", "perm2"]

        request = api_request.get("/test/")
        request.user = mock_user

        permission = HasAllPermissions()
        assert permission.has_permission(request, mock_view) is False


class TestCanViewAssets:
    """Tests for CanViewAssets permission shortcut."""

    def test_user_can_view_assets(self, api_request, mock_view, mock_user):
        """Test user with assets.view permission is allowed."""
        mock_user.permissions = {"assets.view"}

        request = api_request.get("/test/")
        request.user = mock_user

        permission = CanViewAssets()
        assert permission.has_permission(request, mock_view) is True

    def test_user_cannot_view_assets(self, api_request, mock_view, mock_user):
        """Test user without assets.view permission is denied."""
        mock_user.permissions = set()

        request = api_request.get("/test/")
        request.user = mock_user

        permission = CanViewAssets()
        assert permission.has_permission(request, mock_view) is False


class TestCanManageAssets:
    """Tests for CanManageAssets permission shortcut."""

    def test_get_requires_view(self, api_request, mock_view, mock_user):
        """Test GET requires assets.view permission."""
        mock_user.permissions = {"assets.view"}

        request = api_request.get("/test/")
        request.user = mock_user

        permission = CanManageAssets()
        assert permission.has_permission(request, mock_view) is True

    def test_post_requires_create(self, api_request, mock_view, mock_user):
        """Test POST requires assets.create permission."""
        mock_user.permissions = {"assets.create"}

        request = api_request.post("/test/", {})
        request.user = mock_user

        permission = CanManageAssets()
        assert permission.has_permission(request, mock_view) is True

    def test_put_requires_update(self, api_request, mock_view, mock_user):
        """Test PUT requires assets.update permission."""
        mock_user.permissions = {"assets.update"}

        request = api_request.put("/test/", {})
        request.user = mock_user

        permission = CanManageAssets()
        assert permission.has_permission(request, mock_view) is True

    def test_delete_requires_delete(self, api_request, mock_view, mock_user):
        """Test DELETE requires assets.delete permission."""
        mock_user.permissions = {"assets.delete"}

        request = api_request.delete("/test/")
        request.user = mock_user

        permission = CanManageAssets()
        assert permission.has_permission(request, mock_view) is True


class TestCanViewAlerts:
    """Tests for CanViewAlerts permission shortcut."""

    def test_user_can_view_alerts(self, api_request, mock_view, mock_user):
        """Test user with alerts.view permission is allowed."""
        mock_user.permissions = {"alerts.view"}

        request = api_request.get("/test/")
        request.user = mock_user

        permission = CanViewAlerts()
        assert permission.has_permission(request, mock_view) is True


class TestCanAcknowledgeAlerts:
    """Tests for CanAcknowledgeAlerts permission shortcut."""

    def test_user_can_acknowledge(self, api_request, mock_view, mock_user):
        """Test user with alerts.acknowledge permission is allowed."""
        mock_user.permissions = {"alerts.acknowledge"}

        request = api_request.post("/test/")
        request.user = mock_user

        permission = CanAcknowledgeAlerts()
        assert permission.has_permission(request, mock_view) is True


class TestAreaAccessPermission:
    """Tests for AreaAccessPermission."""

    def test_superuser_can_access_all(self, api_request, mock_view, mock_user):
        """Test that superusers can access all areas."""
        mock_user.is_superuser = True

        request = api_request.get("/test/")
        request.user = mock_user

        obj = MagicMock()
        obj.area_code = "restricted-area"

        permission = AreaAccessPermission()
        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_user_can_access_allowed_area(self, api_request, mock_view, mock_user):
        """Test that users can access their allowed areas."""
        mock_user.allowed_areas = ["melt-shop"]

        request = api_request.get("/test/")
        request.user = mock_user

        obj = MagicMock()
        obj.area_code = "melt-shop"

        permission = AreaAccessPermission()
        assert permission.has_object_permission(request, mock_view, obj) is True

    def test_user_cannot_access_restricted_area(
        self, api_request, mock_view, mock_user
    ):
        """Test that users cannot access areas not in their allowed list."""
        mock_user.allowed_areas = ["melt-shop"]

        request = api_request.get("/test/")
        request.user = mock_user

        obj = MagicMock()
        obj.area_code = "finishing"

        permission = AreaAccessPermission()
        assert permission.has_object_permission(request, mock_view, obj) is False
