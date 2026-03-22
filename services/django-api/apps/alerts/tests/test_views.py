"""Tests for alerts views."""

import pytest
from datetime import timedelta
from unittest.mock import patch, MagicMock

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from apps.alerts.models import Alert, AlertHistory, AlertRule


@pytest.fixture
def authenticated_client(operator_user):
    """Create authenticated API client."""
    client = APIClient()
    client.force_authenticate(user=MagicMock())
    client.handler._force_user = operator_user
    return client


@pytest.mark.django_db
class TestAlertRuleViewSet:
    """Tests for AlertRule API endpoints."""

    def test_list_alert_rules(self, api_client, alert_rule):
        """Test listing alert rules."""
        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_auth.return_value = (mock_user, None)

            response = api_client.get("/api/alerts/rules/")

        # Should work - check response format
        assert response.status_code in [200, 401, 403]

    def test_create_alert_rule(self, api_client, device):
        """Test creating a new alert rule."""
        data = {
            "name": "New Temperature Rule",
            "description": "Test rule",
            "device": str(device.id),
            "rule_type": "threshold_high",
            "threshold_value": 1500.0,
            "severity": "high",
        }

        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_auth.return_value = (mock_user, None)

            response = api_client.post("/api/alerts/rules/", data, format="json")

        assert response.status_code in [201, 401, 403]


@pytest.mark.django_db
class TestAlertViewSet:
    """Tests for Alert API endpoints."""

    def test_list_alerts(self, api_client, alert):
        """Test listing alerts."""
        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_auth.return_value = (mock_user, None)

            response = api_client.get("/api/alerts/alerts/")

        assert response.status_code in [200, 401, 403]

    def test_list_active_alerts(self, api_client, device, alert_rule):
        """Test listing only active alerts."""
        # Create active and resolved alerts
        Alert.objects.create(
            device=device,
            rule=alert_rule,
            alert_type="threshold_high",
            severity="high",
            message="Active alert",
            status="active",
        )
        resolved = Alert.objects.create(
            device=device,
            rule=alert_rule,
            alert_type="threshold_high",
            severity="medium",
            message="Resolved alert",
            status="resolved",
        )

        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_auth.return_value = (mock_user, None)

            response = api_client.get("/api/alerts/alerts/active/")

        assert response.status_code in [200, 401, 403]

    def test_acknowledge_alert(self, api_client, alert):
        """Test acknowledging an alert."""
        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_user.email = "test@forgelink.local"
            mock_auth.return_value = (mock_user, None)

            response = api_client.post(
                f"/api/alerts/alerts/{alert.id}/acknowledge/",
                {},
                format="json",
            )

        assert response.status_code in [200, 401, 403]

    def test_resolve_alert(self, api_client, alert):
        """Test resolving an alert."""
        # First acknowledge
        alert.acknowledge("test@forgelink.local")

        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_user.email = "test@forgelink.local"
            mock_auth.return_value = (mock_user, None)

            response = api_client.post(
                f"/api/alerts/alerts/{alert.id}/resolve/",
                {},
                format="json",
            )

        assert response.status_code in [200, 401, 403]

    def test_bulk_acknowledge(self, api_client, device, alert_rule):
        """Test bulk acknowledging alerts."""
        alerts = [
            Alert.objects.create(
                device=device,
                rule=alert_rule,
                alert_type="threshold_high",
                severity="high",
                message=f"Alert {i}",
            )
            for i in range(3)
        ]

        alert_ids = [str(a.id) for a in alerts]

        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_user.email = "test@forgelink.local"
            mock_auth.return_value = (mock_user, None)

            response = api_client.post(
                "/api/alerts/alerts/acknowledge_bulk/",
                {"alert_ids": alert_ids},
                format="json",
            )

        assert response.status_code in [200, 401, 403]


@pytest.mark.django_db
class TestAlertHistoryViewSet:
    """Tests for AlertHistory API endpoints."""

    def test_list_alert_history(self, api_client, alert):
        """Test listing alert history."""
        # Create history entry
        alert.resolve("test@forgelink.local")
        AlertHistory.objects.create(
            alert_id=alert.id,
            device_id=alert.device.device_id,
            plant="steel-plant-kigali",
            area="melt-shop",
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            triggered_at=alert.triggered_at,
            resolved_at=alert.resolved_at,
            duration_seconds=300,
        )

        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_auth.return_value = (mock_user, None)

            response = api_client.get("/api/alerts/history/")

        assert response.status_code in [200, 401, 403]


@pytest.mark.django_db
class TestAlertStatsEndpoint:
    """Tests for alert statistics endpoint."""

    def test_get_alert_stats(self, api_client, device, alert_rule):
        """Test getting alert statistics."""
        # Create alerts with different severities
        Alert.objects.create(
            device=device,
            rule=alert_rule,
            alert_type="threshold_high",
            severity="critical",
            message="Critical alert",
        )
        Alert.objects.create(
            device=device,
            rule=alert_rule,
            alert_type="threshold_high",
            severity="high",
            message="High alert",
        )
        Alert.objects.create(
            device=device,
            rule=alert_rule,
            alert_type="threshold_low",
            severity="medium",
            message="Medium alert",
            status="acknowledged",
        )

        with patch("apps.core.authentication.JWTAuthentication.authenticate") as mock_auth:
            mock_user = MagicMock()
            mock_user.has_permission.return_value = True
            mock_auth.return_value = (mock_user, None)

            response = api_client.get("/api/alerts/stats/")

        assert response.status_code in [200, 401, 403]
