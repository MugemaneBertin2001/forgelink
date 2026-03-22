"""Tests for audit models."""

import pytest
from datetime import date, timedelta
from django.utils import timezone

from apps.audit.models import AuditLog, AuditSummary


@pytest.mark.django_db
class TestAuditLogModel:
    """Tests for AuditLog model."""

    def test_create_audit_log(self):
        """Test creating an audit log entry."""
        log = AuditLog.objects.create(
            user_id="test@forgelink.local",
            role_code="PLANT_OPERATOR",
            action="create",
            resource="/api/alerts/",
            resource_type="Alert",
            method="POST",
            ip_address="192.168.1.1",
            status_code=201,
            duration_ms=150,
        )

        assert log.user_id == "test@forgelink.local"
        assert log.action == "create"
        assert log.status_code == 201

    def test_audit_log_str(self):
        """Test audit log string representation."""
        log = AuditLog.objects.create(
            user_id="test@forgelink.local",
            action="update",
            resource="/api/devices/123/",
        )

        log_str = str(log)
        assert "test@forgelink.local" in log_str
        assert "update" in log_str

    def test_audit_log_class_method(self):
        """Test AuditLog.log() class method."""
        log = AuditLog.log(
            action="delete",
            resource="/api/alerts/456/",
            user_id="admin@forgelink.local",
            status_code=204,
        )

        assert log.action == "delete"
        assert log.user_id == "admin@forgelink.local"

    def test_audit_log_with_details(self):
        """Test audit log with JSON details."""
        details = {
            "old_value": 100,
            "new_value": 200,
            "field": "threshold",
        }

        log = AuditLog.objects.create(
            user_id="test@forgelink.local",
            action="update",
            resource="/api/rules/789/",
            details=details,
        )

        assert log.details["old_value"] == 100
        assert log.details["new_value"] == 200

    def test_audit_log_action_types(self):
        """Test all action types are valid."""
        for action_type, _ in AuditLog.ActionType.choices:
            log = AuditLog.objects.create(
                action=action_type,
                resource="/test/",
            )
            assert log.action == action_type

    def test_audit_log_ordering(self):
        """Test that logs are ordered by timestamp descending."""
        old_log = AuditLog.objects.create(
            action="create",
            resource="/test/1/",
            timestamp=timezone.now() - timedelta(hours=1),
        )
        new_log = AuditLog.objects.create(
            action="create",
            resource="/test/2/",
        )

        logs = list(AuditLog.objects.all())
        assert logs[0].id == new_log.id
        assert logs[1].id == old_log.id


@pytest.mark.django_db
class TestAuditSummaryModel:
    """Tests for AuditSummary model."""

    def test_create_summary(self):
        """Test creating an audit summary."""
        summary = AuditSummary.objects.create(
            date=date.today(),
            total_requests=1000,
            successful_requests=950,
            failed_requests=50,
            unique_users=25,
        )

        assert summary.total_requests == 1000
        assert summary.failed_requests == 50

    def test_summary_str(self):
        """Test summary string representation."""
        summary = AuditSummary.objects.create(
            date=date.today(),
        )

        assert str(date.today()) in str(summary)

    def test_generate_for_date(self):
        """Test generating summary from audit logs."""
        target_date = date.today()

        # Create some audit logs for today
        for i in range(10):
            AuditLog.objects.create(
                user_id=f"user{i % 3}@test.com",
                action="create" if i % 2 == 0 else "read",
                resource=f"/api/test/{i}/",
                status_code=200 if i < 8 else 500,
            )

        summary = AuditSummary.generate_for_date(target_date)

        assert summary.total_requests == 10
        assert summary.unique_users == 3
        assert summary.successful_requests == 8
        assert summary.failed_requests == 2

    def test_generate_for_date_updates_existing(self):
        """Test that generate_for_date updates existing summary."""
        target_date = date.today()

        # Create initial summary
        AuditSummary.objects.create(
            date=target_date,
            total_requests=5,
        )

        # Create some logs
        for i in range(3):
            AuditLog.objects.create(
                action="create",
                resource=f"/api/test/{i}/",
                status_code=200,
            )

        # Regenerate
        summary = AuditSummary.generate_for_date(target_date)

        assert summary.total_requests == 3  # Updated to new count
        assert AuditSummary.objects.filter(date=target_date).count() == 1

    def test_summary_top_resources(self):
        """Test top resources aggregation."""
        target_date = date.today()

        # Create logs with varying resources
        for i in range(5):
            AuditLog.objects.create(
                action="read",
                resource="/api/popular/",
                status_code=200,
            )
        for i in range(2):
            AuditLog.objects.create(
                action="read",
                resource="/api/less-popular/",
                status_code=200,
            )

        summary = AuditSummary.generate_for_date(target_date)

        assert len(summary.top_resources) >= 1
        # Most popular should be first
        assert summary.top_resources[0]["resource"] == "/api/popular/"
        assert summary.top_resources[0]["count"] == 5

    def test_summary_action_counts(self):
        """Test action type counting."""
        target_date = date.today()

        AuditLog.objects.create(action="create", resource="/test/", status_code=201)
        AuditLog.objects.create(action="create", resource="/test/", status_code=201)
        AuditLog.objects.create(action="read", resource="/test/", status_code=200)
        AuditLog.objects.create(action="acknowledge", resource="/test/", status_code=200)

        summary = AuditSummary.generate_for_date(target_date)

        assert summary.create_count == 2
        assert summary.read_count == 1
        assert summary.alert_acknowledge_count == 1
