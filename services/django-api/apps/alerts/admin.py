"""Django Unfold admin for alerts."""

from django.contrib import admin
from django.utils.html import format_html

from unfold.admin import ModelAdmin
from unfold.decorators import display

from .models import Alert, AlertHistory, AlertRule


@admin.register(AlertRule)
class AlertRuleAdmin(ModelAdmin):
    list_display = [
        "name",
        "rule_type_badge",
        "severity_badge",
        "target_display",
        "threshold_display",
        "is_active_badge",
        "notify_slack",
    ]
    list_filter = ["severity", "rule_type", "is_active", "notify_slack"]
    search_fields = ["name", "description", "device__device_id", "area_code"]
    readonly_fields = ["id", "created_at", "updated_at"]

    fieldsets = (
        (None, {"fields": ("name", "description")}),
        (
            "Target",
            {
                "fields": ("device", "device_type", "area_code"),
                "description": "Leave all blank to apply to all devices",
            },
        ),
        (
            "Rule Configuration",
            {
                "fields": (
                    "rule_type",
                    "severity",
                    "threshold_value",
                    "threshold_low",
                    "threshold_high",
                    "rate_threshold",
                    "stale_minutes",
                )
            },
        ),
        (
            "Notifications",
            {"fields": ("notify_slack", "slack_channel", "cooldown_minutes")},
        ),
        ("Status", {"fields": ("is_active",)}),
        (
            "Metadata",
            {
                "fields": ("id", "created_by", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    @display(description="Type")
    def rule_type_badge(self, obj):
        return obj.get_rule_type_display()

    @display(description="Severity")
    def severity_badge(self, obj):
        colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#d97706",
            "low": "#2563eb",
            "info": "#6b7280",
        }
        color = colors.get(obj.severity, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.severity,
        )

    @display(description="Target")
    def target_display(self, obj):
        if obj.device:
            return obj.device.device_id
        elif obj.device_type:
            return f"Type: {obj.device_type.code}"
        elif obj.area_code:
            return f"Area: {obj.area_code}"
        return "All devices"

    @display(description="Threshold")
    def threshold_display(self, obj):
        if obj.rule_type == "threshold_range":
            return f"{obj.threshold_low} - {obj.threshold_high}"
        elif obj.threshold_value:
            return str(obj.threshold_value)
        elif obj.stale_minutes:
            return f"{obj.stale_minutes} min"
        return "-"

    @display(description="Active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active


@admin.register(Alert)
class AlertAdmin(ModelAdmin):
    list_display = [
        "id_short",
        "device_link",
        "severity_badge",
        "status_badge",
        "message_short",
        "triggered_at",
        "duration_display",
    ]
    list_filter = ["severity", "status", "alert_type", "triggered_at"]
    search_fields = ["device__device_id", "message"]
    readonly_fields = [
        "id",
        "rule",
        "device",
        "alert_type",
        "severity",
        "message",
        "value",
        "threshold",
        "unit",
        "triggered_at",
        "notified_slack",
        "notified_at",
    ]
    date_hierarchy = "triggered_at"
    actions = ["acknowledge_alerts", "resolve_alerts"]

    fieldsets = (
        (None, {"fields": ("id", "device", "rule")}),
        (
            "Alert Details",
            {
                "fields": (
                    "alert_type",
                    "severity",
                    "message",
                    "value",
                    "threshold",
                    "unit",
                )
            },
        ),
        (
            "Status",
            {
                "fields": (
                    "status",
                    "triggered_at",
                    "acknowledged_at",
                    "acknowledged_by",
                    "resolved_at",
                    "resolved_by",
                )
            },
        ),
        ("Notifications", {"fields": ("notified_slack", "notified_at")}),
    )

    @display(description="ID")
    def id_short(self, obj):
        return str(obj.id)[:8]

    @display(description="Device")
    def device_link(self, obj):
        return obj.device.device_id

    @display(description="Severity")
    def severity_badge(self, obj):
        colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#d97706",
            "low": "#2563eb",
            "info": "#6b7280",
        }
        color = colors.get(obj.severity, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.severity,
        )

    @display(description="Status")
    def status_badge(self, obj):
        colors = {
            "active": "#dc2626",
            "acknowledged": "#d97706",
            "resolved": "#059669",
            "suppressed": "#6b7280",
        }
        color = colors.get(obj.status, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color,
            obj.status,
        )

    @display(description="Message")
    def message_short(self, obj):
        return obj.message[:50] + "..." if len(obj.message) > 50 else obj.message

    @display(description="Duration")
    def duration_display(self, obj):
        secs = obj.duration_seconds
        if secs < 60:
            return f"{secs}s"
        elif secs < 3600:
            return f"{secs // 60}m"
        else:
            return f"{secs // 3600}h {(secs % 3600) // 60}m"

    @admin.action(description="Acknowledge selected alerts")
    def acknowledge_alerts(self, request, queryset):
        count = 0
        for alert in queryset.filter(status="active"):
            alert.acknowledge(
                request.user.email if hasattr(request.user, "email") else "admin"
            )
            count += 1
        self.message_user(request, f"{count} alerts acknowledged.")

    @admin.action(description="Resolve selected alerts")
    def resolve_alerts(self, request, queryset):
        from .services import AlertService

        count = 0
        for alert in queryset.filter(status__in=["active", "acknowledged"]):
            AlertService.resolve_alert(
                str(alert.id),
                request.user.email if hasattr(request.user, "email") else "admin",
            )
            count += 1
        self.message_user(request, f"{count} alerts resolved.")


@admin.register(AlertHistory)
class AlertHistoryAdmin(ModelAdmin):
    list_display = [
        "alert_id_short",
        "device_id",
        "area",
        "severity_badge",
        "triggered_at",
        "duration_display",
        "resolved_by",
    ]
    list_filter = ["severity", "area", "triggered_at"]
    search_fields = ["device_id", "message", "area"]
    readonly_fields = [
        "id",
        "alert_id",
        "rule_id",
        "device_id",
        "plant",
        "area",
        "alert_type",
        "severity",
        "message",
        "value",
        "threshold",
        "triggered_at",
        "acknowledged_at",
        "resolved_at",
        "duration_seconds",
        "acknowledged_by",
        "resolved_by",
        "resolution_notes",
        "archived_at",
    ]
    date_hierarchy = "triggered_at"

    @display(description="Alert ID")
    def alert_id_short(self, obj):
        return str(obj.alert_id)[:8]

    @display(description="Severity")
    def severity_badge(self, obj):
        colors = {
            "critical": "#dc2626",
            "high": "#ea580c",
            "medium": "#d97706",
            "low": "#2563eb",
            "info": "#6b7280",
        }
        color = colors.get(obj.severity, "#6b7280")
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px; text-transform: uppercase;">{}</span>',
            color,
            obj.severity,
        )

    @display(description="Duration")
    def duration_display(self, obj):
        secs = obj.duration_seconds
        if secs < 60:
            return f"{secs}s"
        elif secs < 3600:
            return f"{secs // 60}m"
        else:
            return f"{secs // 3600}h {(secs % 3600) // 60}m"
