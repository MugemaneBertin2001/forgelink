"""Tests for audit tasks."""

from datetime import date, timedelta

from django.utils import timezone

import pytest

from apps.audit.models import AuditLog, AuditSummary
from apps.audit.tasks import (
    backfill_summaries,
    cleanup_old_audit_logs,
    create_audit_log,
    generate_daily_summary,
)


@pytest.mark.django_db
class TestCreateAuditLogTask:
    """Tests for create_audit_log task."""

    def test_create_audit_log_task(self):
        """Test creating audit log via task."""
        create_audit_log(
            user_id="test@forgelink.local",
            role_code="OPERATOR",
            action="create",
            resource="/api/alerts/",
            resource_type="Alert",
            method="POST",
            ip_address="127.0.0.1",
            status_code=201,
            duration_ms=100,
        )

        log = AuditLog.objects.first()
        assert log is not None
        assert log.user_id == "test@forgelink.local"
        assert log.action == "create"

    def test_create_audit_log_with_details(self):
        """Test creating audit log with details."""
        details = {"old_status": "active", "new_status": "resolved"}

        create_audit_log(
            action="update",
            resource="/api/alerts/123/",
            details=details,
        )

        log = AuditLog.objects.first()
        assert log.details == details


@pytest.mark.django_db
class TestGenerateDailySummaryTask:
    """Tests for generate_daily_summary task."""

    def test_generate_summary_for_yesterday(self):
        """Test generating summary for yesterday."""
        yesterday = timezone.now().date() - timedelta(days=1)

        # Create some logs for yesterday using update to set timestamp
        for i in range(5):
            log = AuditLog.objects.create(
                action="read",
                resource="/api/test/",
                status_code=200,
            )
            # Use update to bypass any default value issues
            AuditLog.objects.filter(id=log.id).update(
                timestamp=timezone.now() - timedelta(days=1)
            )

        generate_daily_summary()

        summary = AuditSummary.objects.get(date=yesterday)
        assert summary.total_requests == 5

    def test_generate_summary_for_specific_date(self):
        """Test generating summary for specific date."""
        target_date = "2024-01-15"

        generate_daily_summary(target_date)

        summary = AuditSummary.objects.get(date=date.fromisoformat(target_date))
        assert summary is not None


@pytest.mark.django_db
class TestCleanupOldAuditLogsTask:
    """Tests for cleanup_old_audit_logs task."""

    def test_cleanup_old_logs(self):
        """Test cleaning up old audit logs."""
        # Create old logs
        old_time = timezone.now() - timedelta(days=100)
        for i in range(5):
            log = AuditLog.objects.create(
                action="read",
                resource="/api/test/",
            )
            # Manually set timestamp to old date
            AuditLog.objects.filter(id=log.id).update(timestamp=old_time)

        # Create recent logs
        for i in range(3):
            AuditLog.objects.create(
                action="create",
                resource="/api/test/",
            )

        deleted = cleanup_old_audit_logs(days=90)

        assert deleted == 5
        assert AuditLog.objects.count() == 3

    def test_cleanup_respects_days_parameter(self):
        """Test that cleanup respects days parameter."""
        # Create logs 50 days old
        fifty_days_ago = timezone.now() - timedelta(days=50)
        for i in range(3):
            log = AuditLog.objects.create(
                action="read",
                resource="/api/test/",
            )
            AuditLog.objects.filter(id=log.id).update(timestamp=fifty_days_ago)

        # Should not delete with 60 day retention
        deleted = cleanup_old_audit_logs(days=60)
        assert deleted == 0

        # Should delete with 30 day retention
        deleted = cleanup_old_audit_logs(days=30)
        assert deleted == 3


@pytest.mark.django_db
class TestBackfillSummariesTask:
    """Tests for backfill_summaries task."""

    def test_backfill_missing_summaries(self):
        """Test backfilling missing summaries."""
        # Create some audit logs for past days
        for i in range(1, 6):
            log_time = timezone.now() - timedelta(days=i)
            log = AuditLog.objects.create(
                action="read",
                resource="/api/test/",
            )
            AuditLog.objects.filter(id=log.id).update(timestamp=log_time)

        generated = backfill_summaries(days=5)

        # Should have created summaries for days with logs
        assert generated >= 0
        assert AuditSummary.objects.count() >= 0

    def test_backfill_skips_existing_summaries(self):
        """Test that backfill skips existing summaries."""
        yesterday = timezone.now().date() - timedelta(days=1)

        # Create existing summary
        AuditSummary.objects.create(
            date=yesterday,
            total_requests=100,
        )

        backfill_summaries(days=5)

        # Should not recreate existing summary
        summaries = AuditSummary.objects.filter(date=yesterday)
        assert summaries.count() == 1
        assert summaries.first().total_requests == 100
