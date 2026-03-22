"""Audit serializers for REST API."""

from rest_framework import serializers

from .models import AuditLog, AuditSummary


class AuditLogSerializer(serializers.ModelSerializer):
    """Serializer for audit log entries."""

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user_id",
            "role_code",
            "action",
            "resource",
            "resource_type",
            "resource_id",
            "method",
            "ip_address",
            "status_code",
            "duration_ms",
            "details",
            "timestamp",
        ]
        read_only_fields = fields


class AuditLogListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    class Meta:
        model = AuditLog
        fields = [
            "id",
            "user_id",
            "action",
            "resource",
            "resource_type",
            "status_code",
            "timestamp",
        ]
        read_only_fields = fields


class AuditSummarySerializer(serializers.ModelSerializer):
    """Serializer for audit daily summaries."""

    class Meta:
        model = AuditSummary
        fields = [
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
        ]
        read_only_fields = fields


class AuditStatsSerializer(serializers.Serializer):
    """Serializer for audit statistics."""

    total_logs = serializers.IntegerField()
    logs_today = serializers.IntegerField()
    unique_users_today = serializers.IntegerField()
    failed_requests_today = serializers.IntegerField()
    avg_response_time_today = serializers.FloatField(allow_null=True)
    actions_by_type = serializers.DictField(child=serializers.IntegerField())
    top_users = serializers.ListField(child=serializers.DictField())
    recent_errors = serializers.ListField(child=serializers.DictField())
