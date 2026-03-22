"""Pytest configuration and shared fixtures for ForgeLink tests."""

import uuid
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.test import RequestFactory

from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """API client for REST API tests."""
    return APIClient()


@pytest.fixture
def request_factory():
    """Request factory for creating mock requests."""
    return RequestFactory()


@pytest.fixture
def mock_user():
    """Mock authenticated user with permissions."""

    class MockUser:
        def __init__(self):
            self.id = str(uuid.uuid4())
            self.email = "test@forgelink.local"
            self.is_authenticated = True
            self.is_superuser = False
            self.permissions = set()
            self.role_code = "PLANT_OPERATOR"
            self.allowed_areas = ["melt-shop", "continuous-casting"]

        def has_permission(self, permission):
            return permission in self.permissions

        def has_any_permission(self, *permissions):
            return bool(self.permissions & set(permissions))

        def has_all_permissions(self, *permissions):
            return set(permissions).issubset(self.permissions)

        def can_access_area(self, area_code):
            return area_code in self.allowed_areas

    return MockUser()


@pytest.fixture
def admin_user(mock_user):
    """Mock admin user with all permissions."""
    mock_user.is_superuser = True
    mock_user.role_code = "FACTORY_ADMIN"
    mock_user.permissions = {
        "assets.view",
        "assets.create",
        "assets.update",
        "assets.delete",
        "alerts.view",
        "alerts.acknowledge",
        "alerts.resolve",
        "telemetry.view",
        "admin.view_audit",
    }
    return mock_user


@pytest.fixture
def operator_user(mock_user):
    """Mock operator user with standard permissions."""
    mock_user.role_code = "PLANT_OPERATOR"
    mock_user.permissions = {
        "assets.view",
        "alerts.view",
        "alerts.acknowledge",
        "alerts.resolve",
        "telemetry.view",
    }
    return mock_user


@pytest.fixture
def viewer_user(mock_user):
    """Mock viewer user with read-only permissions."""
    mock_user.role_code = "VIEWER"
    mock_user.permissions = {"assets.view", "alerts.view", "telemetry.view"}
    return mock_user


@pytest.fixture
def authenticated_request(request_factory, operator_user):
    """Create an authenticated request with user attached."""

    def _make_request(method="get", path="/api/test/", data=None):
        method_fn = getattr(request_factory, method.lower())
        request = method_fn(path, data=data, content_type="application/json")
        request.user = operator_user
        request.user_permissions = operator_user.permissions
        request.role_code = operator_user.role_code
        request.jwt_payload = {
            "sub": operator_user.id,
            "email": operator_user.email,
            "role": operator_user.role_code,
        }
        return request

    return _make_request


@pytest.fixture
def mock_tdengine():
    """Mock TDengine connection."""
    with patch("apps.telemetry.tdengine.get_connection") as mock:
        conn = MagicMock()
        mock.return_value.__enter__ = MagicMock(return_value=conn)
        mock.return_value.__exit__ = MagicMock(return_value=None)
        yield conn


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    with patch("confluent_kafka.Producer") as mock:
        producer = MagicMock()
        mock.return_value = producer
        yield producer


@pytest.fixture
def mock_cache():
    """Mock Django cache."""
    with patch("django.core.cache.cache") as mock:
        mock.get.return_value = None
        mock.set.return_value = None
        yield mock


@pytest.fixture
def sample_device_data():
    """Sample device telemetry data."""
    return {
        "device_id": "temp-sensor-001",
        "value": 1580.5,
        "quality": "good",
        "ts": datetime.now(timezone.utc).isoformat(),
        "plant": "steel-plant-kigali",
        "area": "melt-shop",
        "line": "eaf-1",
        "cell": "electrode-a",
        "unit": "celsius",
    }


@pytest.fixture
def sample_alert_data():
    """Sample alert data."""
    return {
        "device_id": "temp-sensor-001",
        "alert_type": "threshold_high",
        "severity": "critical",
        "message": "Temperature exceeded threshold",
        "value": 1650.0,
        "threshold": 1600.0,
        "unit": "celsius",
    }


# Database fixtures for Django models
@pytest.fixture
def permission(db):
    """Create a test permission."""
    from apps.core.models import Permission

    return Permission.objects.create(
        code="test.view",
        name="Test View Permission",
        description="A test permission",
        module="assets",
    )


@pytest.fixture
def role(db, permission):
    """Create a test role with permissions."""
    from apps.core.models import Role

    role = Role.objects.create(
        code="TEST_ROLE",
        name="Test Role",
        description="A test role",
        is_system=False,
        is_active=True,
    )
    role.permissions.add(permission)
    return role


@pytest.fixture
def plant(db):
    """Create a test plant."""
    from apps.assets.models import Plant

    return Plant.objects.create(
        code="test-plant",
        name="Test Plant",
        description="A test plant",
        timezone="Africa/Kigali",
        is_active=True,
    )


@pytest.fixture
def area(db, plant):
    """Create a test area."""
    from apps.assets.models import Area

    return Area.objects.create(
        plant=plant,
        code="test-area",
        name="Test Area",
        description="A test area",
        area_type="melt_shop",
        is_active=True,
    )


@pytest.fixture
def line(db, area):
    """Create a test line."""
    from apps.assets.models import Line

    return Line.objects.create(
        area=area,
        code="test-line",
        name="Test Line",
        description="A test line",
        is_active=True,
    )


@pytest.fixture
def cell(db, line):
    """Create a test cell."""
    from apps.assets.models import Cell

    return Cell.objects.create(
        line=line,
        code="test-cell",
        name="Test Cell",
        description="A test cell",
        is_active=True,
    )


@pytest.fixture
def device_type(db):
    """Create a test device type."""
    from apps.assets.models import DeviceType

    return DeviceType.objects.create(
        code="temperature",
        name="Temperature Sensor",
        description="Measures temperature",
        default_unit="celsius",
        typical_min=0.0,
        typical_max=2000.0,
    )


@pytest.fixture
def device(db, cell, device_type):
    """Create a test device."""
    from apps.assets.models import Device

    return Device.objects.create(
        cell=cell,
        device_type=device_type,
        device_id="test-device-001",
        name="Test Device",
        description="A test device",
        unit="celsius",
        warning_low=100.0,
        warning_high=1500.0,
        critical_low=50.0,
        critical_high=1600.0,
        status="online",
        is_active=True,
    )


@pytest.fixture
def alert_rule(db, device):
    """Create a test alert rule."""
    from apps.alerts.models import AlertRule

    return AlertRule.objects.create(
        name="Test High Temperature Rule",
        description="Alert when temperature exceeds threshold",
        device=device,
        rule_type="threshold_high",
        threshold_value=1600.0,
        severity="critical",
        is_active=True,
    )


@pytest.fixture
def alert(db, device, alert_rule):
    """Create a test alert."""
    from apps.alerts.models import Alert

    return Alert.objects.create(
        device=device,
        rule=alert_rule,
        alert_type="threshold_high",
        severity="critical",
        message="Temperature exceeded threshold",
        value=1650.0,
        threshold=1600.0,
        unit="celsius",
        status="active",
    )
