"""Tests for alerts models."""

import pytest
from datetime import timedelta
from django.utils import timezone

from apps.alerts.models import Alert, AlertHistory, AlertRule


@pytest.mark.django_db
class TestAlertRuleModel:
    """Tests for AlertRule model."""

    def test_create_alert_rule(self, device):
        """Test creating an alert rule."""
        rule = AlertRule.objects.create(
            name="High Temperature Alert",
            description="Alert when temperature exceeds threshold",
            device=device,
            rule_type="threshold_high",
            threshold_value=1600.0,
            severity="critical",
            is_active=True,
        )

        assert rule.name == "High Temperature Alert"
        assert rule.device == device
        assert rule.rule_type == "threshold_high"
        assert rule.severity == "critical"
        assert str(rule) == "High Temperature Alert (critical)"

    def test_alert_rule_with_device_type(self, device_type):
        """Test creating alert rule for device type."""
        rule = AlertRule.objects.create(
            name="All Temperature Sensors",
            device_type=device_type,
            rule_type="threshold_high",
            threshold_value=1500.0,
            severity="high",
        )

        assert rule.device_type == device_type
        assert rule.device is None

    def test_alert_rule_with_area(self):
        """Test creating alert rule for area."""
        rule = AlertRule.objects.create(
            name="Melt Shop Alerts",
            area_code="melt-shop",
            rule_type="stale_data",
            stale_minutes=5,
            severity="medium",
        )

        assert rule.area_code == "melt-shop"
        assert rule.stale_minutes == 5

    def test_alert_rule_range_thresholds(self, device):
        """Test alert rule with range thresholds."""
        rule = AlertRule.objects.create(
            name="Temperature Range",
            device=device,
            rule_type="threshold_range",
            threshold_low=1400.0,
            threshold_high=1650.0,
            severity="high",
        )

        assert rule.threshold_low == 1400.0
        assert rule.threshold_high == 1650.0

    def test_alert_rule_default_cooldown(self, device):
        """Test default cooldown value."""
        rule = AlertRule.objects.create(
            name="Test Rule",
            device=device,
            rule_type="threshold_high",
            threshold_value=100.0,
        )

        assert rule.cooldown_minutes == 5

    def test_alert_rule_slack_notification_defaults(self, device):
        """Test default Slack notification settings."""
        rule = AlertRule.objects.create(
            name="Test Rule",
            device=device,
            rule_type="threshold_high",
            threshold_value=100.0,
        )

        assert rule.notify_slack is True
        assert rule.slack_channel == "#forgelink-alerts"


@pytest.mark.django_db
class TestAlertModel:
    """Tests for Alert model."""

    def test_create_alert(self, device, alert_rule):
        """Test creating an alert."""
        alert = Alert.objects.create(
            device=device,
            rule=alert_rule,
            alert_type="threshold_high",
            severity="critical",
            message="Temperature exceeded 1600°C",
            value=1650.0,
            threshold=1600.0,
            unit="celsius",
        )

        assert alert.status == "active"
        assert alert.value == 1650.0
        assert alert.device == device

    def test_acknowledge_alert(self, alert):
        """Test acknowledging an alert."""
        alert.acknowledge("operator@forgelink.local")

        assert alert.status == "acknowledged"
        assert alert.acknowledged_by == "operator@forgelink.local"
        assert alert.acknowledged_at is not None

    def test_resolve_alert(self, alert):
        """Test resolving an alert."""
        alert.resolve("operator@forgelink.local")

        assert alert.status == "resolved"
        assert alert.resolved_by == "operator@forgelink.local"
        assert alert.resolved_at is not None

    def test_resolve_alert_default_user(self, alert):
        """Test resolving alert with default system user."""
        alert.resolve()

        assert alert.resolved_by == "system"

    def test_duration_seconds_active(self, alert):
        """Test duration calculation for active alert."""
        alert.triggered_at = timezone.now() - timedelta(minutes=5)
        duration = alert.duration_seconds

        assert duration >= 300  # At least 5 minutes

    def test_duration_seconds_resolved(self, alert):
        """Test duration calculation for resolved alert."""
        alert.triggered_at = timezone.now() - timedelta(minutes=10)
        alert.resolved_at = timezone.now() - timedelta(minutes=5)
        duration = alert.duration_seconds

        assert 290 <= duration <= 310  # Approximately 5 minutes

    def test_alert_string_representation(self, alert):
        """Test alert string representation."""
        alert_str = str(alert)
        assert "[critical]" in alert_str
        assert alert.device.device_id in alert_str

    def test_alert_indexes(self):
        """Test that model indexes are defined."""
        indexes = Alert._meta.indexes
        assert len(indexes) == 3  # status/triggered_at, device/triggered_at, severity/status


@pytest.mark.django_db
class TestAlertHistoryModel:
    """Tests for AlertHistory model."""

    def test_create_alert_history(self, alert):
        """Test creating alert history from alert."""
        alert.resolve("operator@forgelink.local")

        history = AlertHistory.objects.create(
            alert_id=alert.id,
            rule_id=alert.rule.id if alert.rule else None,
            device_id=alert.device.device_id,
            plant="steel-plant-kigali",
            area="melt-shop",
            alert_type=alert.alert_type,
            severity=alert.severity,
            message=alert.message,
            value=alert.value,
            threshold=alert.threshold,
            triggered_at=alert.triggered_at,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at,
            duration_seconds=alert.duration_seconds,
            acknowledged_by=alert.acknowledged_by,
            resolved_by=alert.resolved_by,
        )

        assert history.device_id == alert.device.device_id
        assert history.severity == alert.severity
        assert history.duration_seconds > 0

    def test_alert_history_ordering(self, device, alert_rule):
        """Test that history is ordered by triggered_at descending."""
        # Create multiple alerts with different timestamps
        Alert.objects.create(
            device=device,
            rule=alert_rule,
            alert_type="threshold_high",
            severity="high",
            message="Old alert",
            triggered_at=timezone.now() - timedelta(days=1),
        )

        Alert.objects.create(
            device=device,
            rule=alert_rule,
            alert_type="threshold_high",
            severity="high",
            message="New alert",
            triggered_at=timezone.now(),
        )

        alerts = Alert.objects.all()
        assert alerts[0].message == "New alert"
        assert alerts[1].message == "Old alert"
