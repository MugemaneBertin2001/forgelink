"""Audit admin configuration using Django Unfold."""

from django.contrib import admin

from unfold.admin import ModelAdmin

from .models import AuditLog, AuditSummary


@admin.register(AuditLog)
class AuditLogAdmin(ModelAdmin):
    """Admin for audit log entries."""

    list_display = [
        "timestamp",
        "user_id",
        "action",
        "resource_type",
        "resource",
        "status_code",
        "duration_ms",
        "ip_address",
    ]
    list_filter = [
        "action",
        "resource_type",
        "status_code",
        "timestamp",
    ]
    search_fields = ["user_id", "resource", "resource_id", "ip_address"]
    readonly_fields = [
        "id",
        "user_id",
        "role_code",
        "action",
        "resource",
        "resource_type",
        "resource_id",
        "method",
        "ip_address",
        "user_agent",
        "status_code",
        "duration_ms",
        "details",
        "timestamp",
    ]
    ordering = ["-timestamp"]

    fieldsets = (
        (
            "Action",
            {
                "fields": (
                    "action",
                    "resource",
                    "resource_type",
                    "resource_id",
                    "method",
                ),
            },
        ),
        (
            "User",
            {
                "fields": ("user_id", "role_code"),
            },
        ),
        (
            "Request",
            {
                "fields": ("ip_address", "user_agent", "status_code", "duration_ms"),
            },
        ),
        (
            "Details",
            {
                "fields": ("details", "timestamp"),
            },
        ),
    )

    def has_add_permission(self, request):
        """Audit logs are created automatically, not manually."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs are immutable."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs should not be deleted (keep for compliance)."""
        return False


@admin.register(AuditSummary)
class AuditSummaryAdmin(ModelAdmin):
    """Admin for audit daily summaries."""

    list_display = [
        "date",
        "total_requests",
        "successful_requests",
        "failed_requests",
        "unique_users",
        "avg_response_time_ms",
    ]
    list_filter = [
        "date",
    ]
    readonly_fields = [
        "id",
        "date",
        "total_requests",
        "successful_requests",
        "failed_requests",
        "unique_users",
        "login_count",
        "logout_count",
        "create_count",
        "read_count",
        "update_count",
        "delete_count",
        "alert_acknowledge_count",
        "alert_resolve_count",
        "avg_response_time_ms",
        "max_response_time_ms",
        "top_resources",
        "top_users",
        "created_at",
        "updated_at",
    ]
    ordering = ["-date"]

    fieldsets = (
        (
            "Overview",
            {
                "fields": (
                    "date",
                    "total_requests",
                    "successful_requests",
                    "failed_requests",
                ),
            },
        ),
        (
            "User Activity",
            {
                "fields": ("unique_users", "login_count", "logout_count"),
            },
        ),
        (
            "Actions",
            {
                "fields": (
                    "create_count",
                    "read_count",
                    "update_count",
                    "delete_count",
                    "alert_acknowledge_count",
                    "alert_resolve_count",
                ),
            },
        ),
        (
            "Performance",
            {
                "fields": ("avg_response_time_ms", "max_response_time_ms"),
            },
        ),
        (
            "Top Activity",
            {
                "fields": ("top_resources", "top_users"),
            },
        ),
    )

    def has_add_permission(self, request):
        """Summaries are generated automatically."""
        return False

    def has_change_permission(self, request, obj=None):
        """Summaries are read-only."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Summaries should not be deleted."""
        return False
