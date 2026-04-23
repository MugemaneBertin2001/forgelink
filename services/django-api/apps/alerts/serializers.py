"""REST API serializers for alerts."""

from rest_framework import serializers

from .models import Alert, AlertHistory, AlertRule


class AlertRuleSerializer(serializers.ModelSerializer):
    """Serializer for alert rules."""

    device_id = serializers.CharField(source="device.device_id", read_only=True)
    device_type_code = serializers.CharField(source="device_type.code", read_only=True)

    class Meta:
        model = AlertRule
        fields = [
            "id",
            "name",
            "description",
            "device",
            "device_id",
            "device_type",
            "device_type_code",
            "area_code",
            "rule_type",
            "threshold_value",
            "threshold_low",
            "threshold_high",
            "rate_threshold",
            "stale_minutes",
            "severity",
            "notify_slack",
            "slack_channel",
            "notify_email",
            "email_recipients",
            "cooldown_minutes",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class AlertSerializer(serializers.ModelSerializer):
    """Serializer for alerts."""

    device_id = serializers.CharField(source="device.device_id", read_only=True)
    device_name = serializers.CharField(source="device.name", read_only=True)
    area = serializers.CharField(source="device.cell.line.area.code", read_only=True)
    duration_seconds = serializers.ReadOnlyField()

    class Meta:
        model = Alert
        fields = [
            "id",
            "rule",
            "device",
            "device_id",
            "device_name",
            "area",
            "alert_type",
            "severity",
            "message",
            "value",
            "threshold",
            "unit",
            "status",
            "triggered_at",
            "acknowledged_at",
            "acknowledged_by",
            "resolved_at",
            "resolved_by",
            "notified_slack",
            "notified_email",
            "notified_at",
            "duration_seconds",
        ]
        read_only_fields = [
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
            "notified_email",
            "notified_at",
            "duration_seconds",
        ]


class AlertAcknowledgeSerializer(serializers.Serializer):
    """Serializer for acknowledging alerts."""

    user = serializers.CharField(max_length=128)


class AlertResolveSerializer(serializers.Serializer):
    """Serializer for resolving alerts."""

    user = serializers.CharField(max_length=128, required=False, default="system")
    notes = serializers.CharField(max_length=1000, required=False, default="")


class AlertHistorySerializer(serializers.ModelSerializer):
    """Serializer for alert history."""

    class Meta:
        model = AlertHistory
        fields = [
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


class AlertStatsSerializer(serializers.Serializer):
    """Serializer for alert statistics."""

    period_hours = serializers.IntegerField()
    total = serializers.IntegerField()
    active = serializers.IntegerField()
    by_severity = serializers.DictField()
    by_status = serializers.DictField()
