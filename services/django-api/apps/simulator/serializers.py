"""REST API serializers for steel plant simulator."""

from rest_framework import serializers

from .models import (
    DeviceProfile,
    SimulatedDevice,
    SimulatedPLC,
    SimulationEvent,
    SimulationSession,
)


class DeviceProfileSerializer(serializers.ModelSerializer):
    """Serializer for device profile templates."""

    device_count = serializers.SerializerMethodField()

    class Meta:
        model = DeviceProfile
        fields = [
            "id",
            "name",
            "sensor_type",
            "description",
            "min_value",
            "max_value",
            "unit",
            "noise_factor",
            "drift_rate",
            "response_time_ms",
            "dead_band",
            "high_threshold",
            "low_threshold",
            "critical_high",
            "critical_low",
            "mtbf_hours",
            "mttr_minutes",
            "device_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_device_count(self, obj) -> int:
        return obj.devices.count()


class DeviceProfileMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for nested device profiles."""

    class Meta:
        model = DeviceProfile
        fields = ["id", "name", "sensor_type", "unit", "min_value", "max_value"]


class SimulatedDeviceSerializer(serializers.ModelSerializer):
    """Serializer for simulated devices."""

    profile = DeviceProfileMinimalSerializer(read_only=True)
    profile_id = serializers.UUIDField(write_only=True)
    plc_name = serializers.CharField(source="plc.name", read_only=True)
    mqtt_topic = serializers.CharField(read_only=True)
    opc_node_id = serializers.CharField(read_only=True)
    effective_min = serializers.DecimalField(
        max_digits=12, decimal_places=4, read_only=True
    )
    effective_max = serializers.DecimalField(
        max_digits=12, decimal_places=4, read_only=True
    )

    class Meta:
        model = SimulatedDevice
        fields = [
            "id",
            "device_id",
            "name",
            "description",
            "plc",
            "plc_name",
            "profile",
            "profile_id",
            "status",
            "current_value",
            "target_value",
            "quality",
            "sequence_number",
            "mqtt_topic",
            "opc_node_id",
            "effective_min",
            "effective_max",
            "min_value_override",
            "max_value_override",
            "noise_override",
            "simulation_mode",
            "sine_period_seconds",
            "ramp_rate_per_second",
            "fault_type",
            "fault_start",
            "fault_end",
            "messages_sent",
            "last_published_at",
            "last_value_change_at",
            "error_count",
            "last_error",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "current_value",
            "sequence_number",
            "messages_sent",
            "last_published_at",
            "last_value_change_at",
            "error_count",
            "last_error",
            "created_at",
            "updated_at",
        ]


class SimulatedDeviceMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for nested devices."""

    profile_name = serializers.CharField(source="profile.name", read_only=True)
    sensor_type = serializers.CharField(source="profile.sensor_type", read_only=True)
    unit = serializers.CharField(source="profile.unit", read_only=True)

    class Meta:
        model = SimulatedDevice
        fields = [
            "id",
            "device_id",
            "name",
            "status",
            "current_value",
            "quality",
            "profile_name",
            "sensor_type",
            "unit",
        ]


class SimulatedPLCSerializer(serializers.ModelSerializer):
    """Serializer for simulated PLCs."""

    devices = SimulatedDeviceMinimalSerializer(many=True, read_only=True)
    device_count = serializers.SerializerMethodField()
    topic_prefix = serializers.CharField(read_only=True)
    opc_path = serializers.CharField(read_only=True)

    class Meta:
        model = SimulatedPLC
        fields = [
            "id",
            "name",
            "plc_type",
            "description",
            "plant",
            "area",
            "line",
            "cell",
            "topic_prefix",
            "opc_path",
            "opc_namespace",
            "opc_node_id_prefix",
            "is_online",
            "is_simulating",
            "last_heartbeat",
            "scan_rate_ms",
            "publish_rate_ms",
            "ip_address",
            "firmware_version",
            "devices",
            "device_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "last_heartbeat", "created_at", "updated_at"]

    def get_device_count(self, obj) -> int:
        return obj.devices.count()


class SimulatedPLCMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for nested PLCs."""

    class Meta:
        model = SimulatedPLC
        fields = ["id", "name", "area", "line", "is_online", "is_simulating"]


class SimulationSessionSerializer(serializers.ModelSerializer):
    """Serializer for simulation sessions."""

    devices = SimulatedDeviceMinimalSerializer(many=True, read_only=True)
    device_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    plcs = SimulatedPLCMinimalSerializer(many=True, read_only=True)
    plc_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    duration = serializers.SerializerMethodField()

    class Meta:
        model = SimulationSession
        fields = [
            "id",
            "name",
            "description",
            "status",
            "devices",
            "device_ids",
            "plcs",
            "plc_ids",
            "started_at",
            "stopped_at",
            "scheduled_start",
            "scheduled_stop",
            "duration_seconds",
            "duration",
            "scenario",
            "messages_sent",
            "events_generated",
            "faults_injected",
            "error_count",
            "last_error",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "started_at",
            "stopped_at",
            "messages_sent",
            "events_generated",
            "faults_injected",
            "error_count",
            "last_error",
            "created_at",
            "updated_at",
        ]

    def get_duration(self, obj) -> str | None:
        if obj.started_at and obj.stopped_at:
            delta = obj.stopped_at - obj.started_at
            return str(delta).split(".")[0]
        elif obj.started_at:
            from django.utils import timezone

            delta = timezone.now() - obj.started_at
            return str(delta).split(".")[0]
        return None

    def create(self, validated_data):
        device_ids = validated_data.pop("device_ids", [])
        plc_ids = validated_data.pop("plc_ids", [])

        session = SimulationSession.objects.create(**validated_data)

        if device_ids:
            session.devices.set(SimulatedDevice.objects.filter(id__in=device_ids))
        if plc_ids:
            session.plcs.set(SimulatedPLC.objects.filter(id__in=plc_ids))

        return session


class SimulationEventSerializer(serializers.ModelSerializer):
    """Serializer for simulation events."""

    device_id = serializers.CharField(source="device.device_id", read_only=True)
    plc_name = serializers.CharField(source="plc.name", read_only=True)

    class Meta:
        model = SimulationEvent
        fields = [
            "id",
            "event_type",
            "severity",
            "message",
            "device",
            "device_id",
            "plc",
            "plc_name",
            "session",
            "value",
            "threshold",
            "acknowledged",
            "acknowledged_by",
            "acknowledged_at",
            "published_to_mqtt",
            "published_at",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ============================================
# Action Serializers
# ============================================


class DeviceControlSerializer(serializers.Serializer):
    """Serializer for device control actions."""

    action = serializers.ChoiceField(choices=["start", "stop", "restart"])


class DeviceFaultSerializer(serializers.Serializer):
    """Serializer for fault injection."""

    fault_type = serializers.ChoiceField(
        choices=["stuck", "drift", "noise", "spike", "dead", "none"]
    )
    duration_seconds = serializers.IntegerField(required=False, min_value=1)


class DeviceValueSerializer(serializers.Serializer):
    """Serializer for setting device values."""

    value = serializers.DecimalField(max_digits=12, decimal_places=4, required=False)
    target_value = serializers.DecimalField(
        max_digits=12, decimal_places=4, required=False
    )
    quality = serializers.ChoiceField(
        choices=["good", "bad", "uncertain"], required=False
    )


class PLCControlSerializer(serializers.Serializer):
    """Serializer for PLC control actions."""

    action = serializers.ChoiceField(choices=["start", "stop", "online", "offline"])


class SessionControlSerializer(serializers.Serializer):
    """Serializer for session control actions."""

    action = serializers.ChoiceField(choices=["start", "stop", "pause", "resume"])


class BulkDeviceControlSerializer(serializers.Serializer):
    """Serializer for bulk device operations."""

    device_ids = serializers.ListField(child=serializers.UUIDField())
    action = serializers.ChoiceField(choices=["start", "stop", "restart"])


class BulkFaultInjectionSerializer(serializers.Serializer):
    """Serializer for bulk fault injection."""

    device_ids = serializers.ListField(child=serializers.UUIDField())
    fault_type = serializers.ChoiceField(
        choices=["stuck", "drift", "noise", "spike", "dead", "none"]
    )
    duration_seconds = serializers.IntegerField(required=False, min_value=1)


class EventAcknowledgeSerializer(serializers.Serializer):
    """Serializer for event acknowledgement."""

    acknowledged_by = serializers.CharField(max_length=100, required=False)


# ============================================
# Dashboard Serializers
# ============================================


class SimulatorDashboardSerializer(serializers.Serializer):
    """Serializer for simulator dashboard overview."""

    total_plcs = serializers.IntegerField()
    online_plcs = serializers.IntegerField()
    simulating_plcs = serializers.IntegerField()

    total_devices = serializers.IntegerField()
    running_devices = serializers.IntegerField()
    fault_devices = serializers.IntegerField()

    active_sessions = serializers.IntegerField()
    total_messages_sent = serializers.IntegerField()
    unacknowledged_events = serializers.IntegerField()

    devices_by_area = serializers.DictField()
    devices_by_status = serializers.DictField()
    recent_events = SimulationEventSerializer(many=True)


class AreaSummarySerializer(serializers.Serializer):
    """Serializer for area-level summary."""

    area = serializers.CharField()
    area_display = serializers.CharField()
    plc_count = serializers.IntegerField()
    device_count = serializers.IntegerField()
    running_count = serializers.IntegerField()
    fault_count = serializers.IntegerField()
    avg_value = serializers.DecimalField(
        max_digits=12, decimal_places=4, allow_null=True
    )
