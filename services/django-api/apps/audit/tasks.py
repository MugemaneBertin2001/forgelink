"""Audit logging tasks."""
from celery import shared_task
import logging

logger = logging.getLogger(__name__)


@shared_task
def create_audit_log(
    user_id: str = None,
    action: str = None,
    resource: str = None,
    ip_address: str = None,
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
            action=action,
            resource=resource,
            ip_address=ip_address,
            status_code=status_code,
            duration_ms=duration_ms,
            details=details or {},
        )
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
