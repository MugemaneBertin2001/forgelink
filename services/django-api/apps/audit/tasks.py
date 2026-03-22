"""Audit logging tasks."""

import logging
from datetime import timedelta

from django.utils import timezone

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task
def create_audit_log(
    user_id: str = None,
    role_code: str = None,
    action: str = None,
    resource: str = None,
    resource_type: str = None,
    resource_id: str = None,
    method: str = None,
    ip_address: str = None,
    user_agent: str = None,
    status_code: int = None,
    duration_ms: int = None,
    details: dict = None,
):
    """
    Create an audit log entry asynchronously.
    This runs as a Celery task to avoid blocking the request.
    """
    from apps.audit.models import AuditLog

    try:
        AuditLog.objects.create(
            user_id=user_id,
            role_code=role_code,
            action=action,
            resource=resource,
            resource_type=resource_type,
            resource_id=resource_id,
            method=method,
            ip_address=ip_address,
            user_agent=user_agent,
            status_code=status_code,
            duration_ms=duration_ms,
            details=details or {},
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")


@shared_task
def generate_daily_summary(date_str: str = None):
    """
    Generate audit summary for a specific date.
    If no date is provided, generates for yesterday.

    Run daily at 1:00 AM via Celery Beat.
    """
    from datetime import date

    from apps.audit.models import AuditSummary

    try:
        if date_str:
            target_date = date.fromisoformat(date_str)
        else:
            target_date = timezone.now().date() - timedelta(days=1)

        summary = AuditSummary.generate_for_date(target_date)
        logger.info(
            f"Generated audit summary for {target_date}: {summary.total_requests} requests"
        )
        return str(summary.id)
    except Exception as e:
        logger.error(f"Failed to generate audit summary: {e}")
        raise


@shared_task
def cleanup_old_audit_logs(days: int = 90):
    """
    Clean up audit logs older than specified days.
    Keep summaries indefinitely for historical reporting.

    Run weekly via Celery Beat.
    """
    from apps.audit.models import AuditLog

    try:
        cutoff = timezone.now() - timedelta(days=days)
        deleted, _ = AuditLog.objects.filter(timestamp__lt=cutoff).delete()
        logger.info(f"Deleted {deleted} audit logs older than {days} days")
        return deleted
    except Exception as e:
        logger.error(f"Failed to cleanup audit logs: {e}")
        raise


@shared_task
def backfill_summaries(days: int = 30):
    """
    Generate missing audit summaries for the past N days.
    Useful after initial deployment or if scheduled tasks were missed.
    """
    from apps.audit.models import AuditSummary

    try:
        today = timezone.now().date()
        generated = 0

        for i in range(1, days + 1):
            target_date = today - timedelta(days=i)
            if not AuditSummary.objects.filter(date=target_date).exists():
                AuditSummary.generate_for_date(target_date)
                generated += 1

        logger.info(f"Backfilled {generated} audit summaries for past {days} days")
        return generated
    except Exception as e:
        logger.error(f"Failed to backfill audit summaries: {e}")
        raise
