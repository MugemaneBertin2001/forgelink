"""Audit logging models for ForgeLink.

Tracks all significant user actions and API requests for security and compliance.
"""

import uuid

from django.db import models
from django.utils import timezone


class AuditLog(models.Model):
    """Audit log entry for tracking user actions and API requests."""

    class ActionType(models.TextChoices):
        CREATE = "create", "Create"
        READ = "read", "Read"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        LOGIN = "login", "Login"
        LOGOUT = "logout", "Logout"
        EXPORT = "export", "Export"
        ACKNOWLEDGE = "acknowledge", "Acknowledge"
        RESOLVE = "resolve", "Resolve"
        EXECUTE = "execute", "Execute"
        CONFIGURE = "configure", "Configure"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # User information
    user_id = models.CharField(
        max_length=255, null=True, blank=True, db_index=True, help_text="User ID or email"
    )
    role_code = models.CharField(
        max_length=100, null=True, blank=True, help_text="User role at time of action"
    )

    # Action details
    action = models.CharField(
        max_length=50,
        choices=ActionType.choices,
        db_index=True,
        help_text="Type of action performed",
    )
    resource = models.CharField(
        max_length=255,
        db_index=True,
        help_text="Resource path or identifier (e.g., /api/alerts/123)",
    )
    resource_type = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        db_index=True,
        help_text="Type of resource (e.g., Alert, Device, Plant)",
    )
    resource_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        help_text="Specific resource ID if applicable",
    )

    # Request metadata
    method = models.CharField(
        max_length=10, null=True, blank=True, help_text="HTTP method (GET, POST, etc.)"
    )
    ip_address = models.GenericIPAddressField(
        null=True, blank=True, db_index=True, help_text="Client IP address"
    )
    user_agent = models.TextField(null=True, blank=True, help_text="Client user agent string")

    # Response information
    status_code = models.IntegerField(
        null=True, blank=True, db_index=True, help_text="HTTP response status code"
    )
    duration_ms = models.IntegerField(
        null=True, blank=True, help_text="Request duration in milliseconds"
    )

    # Additional context
    details = models.JSONField(
        default=dict, blank=True, help_text="Additional structured details about the action"
    )

    # Timestamps
    timestamp = models.DateTimeField(
        default=timezone.now, db_index=True, help_text="When the action occurred"
    )

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["user_id", "timestamp"]),
            models.Index(fields=["action", "timestamp"]),
            models.Index(fields=["resource_type", "timestamp"]),
            models.Index(fields=["status_code", "timestamp"]),
        ]
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"

    def __str__(self):
        return f"{self.user_id or 'anonymous'} {self.action} {self.resource} at {self.timestamp}"

    @classmethod
    def log(
        cls,
        action: str,
        resource: str,
        user_id: str = None,
        role_code: str = None,
        resource_type: str = None,
        resource_id: str = None,
        method: str = None,
        ip_address: str = None,
        user_agent: str = None,
        status_code: int = None,
        duration_ms: int = None,
        details: dict = None,
    ) -> "AuditLog":
        """Create an audit log entry.

        This is the primary method for logging actions. For async logging,
        use the create_audit_log Celery task instead.
        """
        return cls.objects.create(
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


class AuditSummary(models.Model):
    """Daily aggregated audit statistics for dashboard and reporting."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    date = models.DateField(db_index=True, unique=True)

    # Request counts
    total_requests = models.IntegerField(default=0)
    successful_requests = models.IntegerField(default=0)
    failed_requests = models.IntegerField(default=0)

    # User activity
    unique_users = models.IntegerField(default=0)
    login_count = models.IntegerField(default=0)
    logout_count = models.IntegerField(default=0)

    # Action counts by type
    create_count = models.IntegerField(default=0)
    read_count = models.IntegerField(default=0)
    update_count = models.IntegerField(default=0)
    delete_count = models.IntegerField(default=0)

    # Alert-specific actions
    alert_acknowledge_count = models.IntegerField(default=0)
    alert_resolve_count = models.IntegerField(default=0)

    # Performance metrics
    avg_response_time_ms = models.FloatField(null=True, blank=True)
    max_response_time_ms = models.IntegerField(null=True, blank=True)

    # Top resources and users (JSON for flexibility)
    top_resources = models.JSONField(default=list, blank=True)
    top_users = models.JSONField(default=list, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date"]
        verbose_name = "Audit Summary"
        verbose_name_plural = "Audit Summaries"

    def __str__(self):
        return f"Audit Summary for {self.date}"

    @classmethod
    def generate_for_date(cls, date) -> "AuditSummary":
        """Generate or update summary for a specific date."""
        from django.db.models import Avg, Count, Max

        logs = AuditLog.objects.filter(timestamp__date=date)

        summary, _ = cls.objects.update_or_create(
            date=date,
            defaults={
                "total_requests": logs.count(),
                "successful_requests": logs.filter(status_code__lt=400).count(),
                "failed_requests": logs.filter(status_code__gte=400).count(),
                "unique_users": logs.exclude(user_id__isnull=True)
                .values("user_id")
                .distinct()
                .count(),
                "login_count": logs.filter(action="login").count(),
                "logout_count": logs.filter(action="logout").count(),
                "create_count": logs.filter(action="create").count(),
                "read_count": logs.filter(action="read").count(),
                "update_count": logs.filter(action="update").count(),
                "delete_count": logs.filter(action="delete").count(),
                "alert_acknowledge_count": logs.filter(action="acknowledge").count(),
                "alert_resolve_count": logs.filter(action="resolve").count(),
                "avg_response_time_ms": logs.exclude(duration_ms__isnull=True).aggregate(
                    avg=Avg("duration_ms")
                )["avg"],
                "max_response_time_ms": logs.exclude(duration_ms__isnull=True).aggregate(
                    max=Max("duration_ms")
                )["max"],
                "top_resources": list(
                    logs.values("resource")
                    .annotate(count=Count("id"))
                    .order_by("-count")[:10]
                ),
                "top_users": list(
                    logs.exclude(user_id__isnull=True)
                    .values("user_id")
                    .annotate(count=Count("id"))
                    .order_by("-count")[:10]
                ),
            },
        )
        return summary
