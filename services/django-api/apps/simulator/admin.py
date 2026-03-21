"""Django Unfold admin configuration for steel plant simulator."""

from django.contrib import admin
from django.utils import timezone

from unfold.admin import ModelAdmin, TabularInline
from unfold.contrib.filters.admin import (
    ChoicesDropdownFilter,
    RangeDateFilter,
    RangeDateTimeFilter,
)
from unfold.decorators import action, display

from .models import (
    DeviceProfile,
    SimulatedDevice,
    SimulatedPLC,
    SimulationEvent,
    SimulationSession,
)


@admin.register(DeviceProfile)
class DeviceProfileAdmin(ModelAdmin):
    """Admin for sensor profile templates with Unfold styling."""

    list_display = [
        "name",
        "sensor_type_display",
        "value_range_display",
        "unit",
        "noise_display",
        "device_count",
        "created_at",
    ]
    list_filter = [
        ("sensor_type", ChoicesDropdownFilter),
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["name", "description"]
    readonly_fields = ["id", "created_at", "updated_at"]
    list_filter_submit = True
    compressed_fields = True

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "name", "sensor_type", "description"),
                "classes": ["tab"],
            },
        ),
        (
            "Value Range",
            {
                "fields": ("min_value", "max_value", "unit"),
                "classes": ["tab"],
            },
        ),
        (
            "Physics Simulation",
            {
                "fields": (
                    "noise_factor",
                    "drift_rate",
                    "response_time_ms",
                    "dead_band",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Thresholds",
            {
                "fields": (
                    "low_threshold",
                    "high_threshold",
                    "critical_low",
                    "critical_high",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Reliability (MTBF/MTTR)",
            {
                "fields": ("mtbf_hours", "mttr_minutes"),
                "classes": ["tab"],
            },
        ),
    )

    @display(description="Sensor Type", label=True)
    def sensor_type_display(self, obj):
        colors = {
            "temperature": "danger",
            "pressure": "info",
            "flow": "primary",
            "level": "warning",
            "vibration": "success",
            "current": "danger",
            "voltage": "warning",
        }
        return obj.sensor_type, colors.get(obj.sensor_type, "secondary")

    @display(description="Range")
    def value_range_display(self, obj):
        return f"{obj.min_value} - {obj.max_value}"

    @display(description="Noise")
    def noise_display(self, obj):
        return f"{float(obj.noise_factor) * 100:.1f}%"

    @display(description="Devices")
    def device_count(self, obj):
        return obj.devices.count()


class SimulatedDeviceInline(TabularInline):
    """Inline admin for devices within a PLC."""

    model = SimulatedDevice
    extra = 0
    fields = ["device_id", "name", "profile", "status", "current_value", "quality"]
    readonly_fields = ["current_value", "quality"]
    show_change_link = True
    tab = True


@admin.register(SimulatedPLC)
class SimulatedPLCAdmin(ModelAdmin):
    """Admin for simulated PLCs with Unfold styling."""

    list_display = [
        "name",
        "plc_type_display",
        "area_display",
        "line",
        "cell",
        "status_display",
        "device_count",
        "last_heartbeat",
    ]
    list_filter = [
        ("plc_type", ChoicesDropdownFilter),
        ("area", ChoicesDropdownFilter),
        "is_online",
        "is_simulating",
    ]
    search_fields = ["name", "description", "line", "cell"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "last_heartbeat",
        "topic_prefix",
        "opc_path",
    ]
    inlines = [SimulatedDeviceInline]
    list_filter_submit = True
    warn_unsaved_form = True

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "name", "plc_type", "description"),
                "classes": ["tab"],
            },
        ),
        (
            "Location (ISA-95 Hierarchy)",
            {
                "fields": ("plant", "area", "line", "cell"),
                "classes": ["tab"],
            },
        ),
        (
            "Generated Paths",
            {
                "fields": ("topic_prefix", "opc_path"),
                "classes": ["tab"],
            },
        ),
        (
            "OPC-UA Configuration",
            {
                "fields": ("opc_namespace", "opc_node_id_prefix"),
                "classes": ["tab"],
            },
        ),
        (
            "Status",
            {
                "fields": ("is_online", "is_simulating", "last_heartbeat"),
                "classes": ["tab"],
            },
        ),
        (
            "Communication",
            {
                "fields": (
                    "scan_rate_ms",
                    "publish_rate_ms",
                    "ip_address",
                    "firmware_version",
                ),
                "classes": ["tab"],
            },
        ),
    )

    actions_detail = ["start_plc_simulation", "stop_plc_simulation"]
    actions = ["start_simulation", "stop_simulation", "bring_online", "take_offline"]

    @display(description="Type", label=True)
    def plc_type_display(self, obj):
        colors = {
            "siemens_s7": "primary",
            "allen_bradley": "success",
            "schneider": "warning",
            "generic": "secondary",
        }
        return obj.get_plc_type_display(), colors.get(obj.plc_type, "secondary")

    @display(description="Area", label=True)
    def area_display(self, obj):
        colors = {
            "melt-shop": "danger",
            "continuous-casting": "warning",
            "rolling-mill": "info",
            "finishing": "success",
        }
        return obj.get_area_display(), colors.get(obj.area, "secondary")

    @display(description="Status", label=True)
    def status_display(self, obj):
        if obj.is_simulating:
            return "SIMULATING", "success"
        elif obj.is_online:
            return "ONLINE", "info"
        else:
            return "OFFLINE", "secondary"

    @display(description="Devices")
    def device_count(self, obj):
        return obj.devices.count()

    @action(description="Start simulation")
    def start_plc_simulation(self, request, object_id):
        plc = SimulatedPLC.objects.get(pk=object_id)
        plc.is_simulating = True
        plc.is_online = True
        plc.last_heartbeat = timezone.now()
        plc.save()

    @action(description="Stop simulation")
    def stop_plc_simulation(self, request, object_id):
        plc = SimulatedPLC.objects.get(pk=object_id)
        plc.is_simulating = False
        plc.save()

    @admin.action(description="Start simulation for selected PLCs")
    def start_simulation(self, request, queryset):
        count = queryset.update(
            is_simulating=True, is_online=True, last_heartbeat=timezone.now()
        )
        self.message_user(request, f"Started simulation for {count} PLCs.")

    @admin.action(description="Stop simulation for selected PLCs")
    def stop_simulation(self, request, queryset):
        count = queryset.update(is_simulating=False)
        self.message_user(request, f"Stopped simulation for {count} PLCs.")

    @admin.action(description="Bring selected PLCs online")
    def bring_online(self, request, queryset):
        count = queryset.update(is_online=True, last_heartbeat=timezone.now())
        self.message_user(request, f"Brought {count} PLCs online.")

    @admin.action(description="Take selected PLCs offline")
    def take_offline(self, request, queryset):
        count = queryset.update(is_online=False, is_simulating=False)
        self.message_user(request, f"Took {count} PLCs offline.")


@admin.register(SimulatedDevice)
class SimulatedDeviceAdmin(ModelAdmin):
    """Admin for individual simulated devices with Unfold styling."""

    list_display = [
        "device_id",
        "name",
        "plc",
        "profile_display",
        "status_display",
        "current_value_display",
        "quality_display",
        "fault_display",
        "messages_sent",
    ]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("quality", ChoicesDropdownFilter),
        ("profile__sensor_type", ChoicesDropdownFilter),
        ("plc__area", ChoicesDropdownFilter),
        ("simulation_mode", ChoicesDropdownFilter),
        ("fault_type", ChoicesDropdownFilter),
    ]
    search_fields = ["device_id", "name", "description"]
    readonly_fields = [
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
        "mqtt_topic",
        "opc_node_id",
        "effective_min",
        "effective_max",
        "value_range",
    ]
    autocomplete_fields = ["plc", "profile"]
    list_select_related = ["plc", "profile"]
    list_filter_submit = True
    warn_unsaved_form = True
    compressed_fields = True

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "device_id", "name", "description", "plc", "profile"),
                "classes": ["tab"],
            },
        ),
        (
            "Current State",
            {
                "fields": (
                    "status",
                    "current_value",
                    "target_value",
                    "quality",
                    "sequence_number",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Topic/Node Mapping",
            {
                "fields": ("mqtt_topic", "opc_node_id"),
                "classes": ["tab"],
            },
        ),
        (
            "Value Configuration",
            {
                "fields": (
                    "min_value_override",
                    "max_value_override",
                    "noise_override",
                    "effective_min",
                    "effective_max",
                    "value_range",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Simulation Behavior",
            {
                "fields": (
                    "simulation_mode",
                    "sine_period_seconds",
                    "ramp_rate_per_second",
                ),
                "classes": ["tab"],
            },
        ),
        (
            "Fault Injection",
            {
                "fields": ("fault_type", "fault_start", "fault_end"),
                "classes": ["tab"],
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "messages_sent",
                    "last_published_at",
                    "last_value_change_at",
                    "error_count",
                    "last_error",
                ),
                "classes": ["tab"],
            },
        ),
    )

    actions_detail = [
        "start_device",
        "stop_device",
        "inject_stuck_fault",
        "inject_drift_fault",
        "inject_spike_fault",
        "clear_device_fault",
    ]
    actions = [
        "start_devices",
        "stop_devices",
        "inject_fault_stuck",
        "inject_fault_drift",
        "inject_fault_spike",
        "clear_faults",
    ]

    @display(description="Profile", label=True)
    def profile_display(self, obj):
        colors = {
            "temperature": "danger",
            "pressure": "info",
            "flow": "primary",
            "level": "warning",
            "vibration": "success",
        }
        return obj.profile.name, colors.get(obj.profile.sensor_type, "secondary")

    @display(description="Status", label=True)
    def status_display(self, obj):
        colors = {
            "offline": "secondary",
            "online": "info",
            "running": "success",
            "fault": "danger",
            "maintenance": "warning",
        }
        return obj.status.upper(), colors.get(obj.status, "secondary")

    @display(description="Value")
    def current_value_display(self, obj):
        if obj.current_value is None:
            return "-"
        return f"{obj.current_value:.2f} {obj.profile.unit}"

    @display(description="Quality", label=True)
    def quality_display(self, obj):
        colors = {
            "good": "success",
            "bad": "danger",
            "uncertain": "warning",
        }
        return obj.quality.upper(), colors.get(obj.quality, "secondary")

    @display(description="Fault", label=True)
    def fault_display(self, obj):
        if obj.fault_type == "none":
            return "NONE", "secondary"
        return obj.fault_type.upper(), "danger"

    # Detail actions
    @action(description="Start device")
    def start_device(self, request, object_id):
        device = SimulatedDevice.objects.get(pk=object_id)
        device.status = "running"
        device.quality = "good"
        device.save()

    @action(description="Stop device")
    def stop_device(self, request, object_id):
        device = SimulatedDevice.objects.get(pk=object_id)
        device.status = "offline"
        device.save()

    @action(description="Inject STUCK fault")
    def inject_stuck_fault(self, request, object_id):
        device = SimulatedDevice.objects.get(pk=object_id)
        device.fault_type = "stuck"
        device.fault_start = timezone.now()
        device.quality = "bad"
        device.save()

    @action(description="Inject DRIFT fault")
    def inject_drift_fault(self, request, object_id):
        device = SimulatedDevice.objects.get(pk=object_id)
        device.fault_type = "drift"
        device.fault_start = timezone.now()
        device.quality = "uncertain"
        device.save()

    @action(description="Inject SPIKE fault")
    def inject_spike_fault(self, request, object_id):
        device = SimulatedDevice.objects.get(pk=object_id)
        device.fault_type = "spike"
        device.fault_start = timezone.now()
        device.quality = "uncertain"
        device.save()

    @action(description="Clear fault")
    def clear_device_fault(self, request, object_id):
        device = SimulatedDevice.objects.get(pk=object_id)
        device.fault_type = "none"
        device.fault_end = timezone.now()
        device.quality = "good"
        device.save()

    # Bulk actions
    @admin.action(description="Start selected devices")
    def start_devices(self, request, queryset):
        count = queryset.update(status="running", quality="good")
        self.message_user(request, f"Started {count} devices.")

    @admin.action(description="Stop selected devices")
    def stop_devices(self, request, queryset):
        count = queryset.update(status="offline")
        self.message_user(request, f"Stopped {count} devices.")

    @admin.action(description="Inject STUCK fault")
    def inject_fault_stuck(self, request, queryset):
        count = queryset.update(
            fault_type="stuck", fault_start=timezone.now(), quality="bad"
        )
        self.message_user(request, f"Injected stuck fault on {count} devices.")

    @admin.action(description="Inject DRIFT fault")
    def inject_fault_drift(self, request, queryset):
        count = queryset.update(
            fault_type="drift", fault_start=timezone.now(), quality="uncertain"
        )
        self.message_user(request, f"Injected drift fault on {count} devices.")

    @admin.action(description="Inject SPIKE fault")
    def inject_fault_spike(self, request, queryset):
        count = queryset.update(
            fault_type="spike", fault_start=timezone.now(), quality="uncertain"
        )
        self.message_user(request, f"Injected spike fault on {count} devices.")

    @admin.action(description="Clear all faults")
    def clear_faults(self, request, queryset):
        count = queryset.update(
            fault_type="none",
            fault_start=None,
            fault_end=timezone.now(),
            quality="good",
        )
        self.message_user(request, f"Cleared faults on {count} devices.")


@admin.register(SimulationSession)
class SimulationSessionAdmin(ModelAdmin):
    """Admin for simulation sessions with Unfold styling."""

    list_display = [
        "name",
        "status_display",
        "device_count",
        "plc_count",
        "messages_sent",
        "events_generated",
        "duration_display",
        "created_at",
    ]
    list_filter = [
        ("status", ChoicesDropdownFilter),
        ("created_at", RangeDateFilter),
    ]
    search_fields = ["name", "description"]
    readonly_fields = [
        "id",
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
    filter_horizontal = ["devices", "plcs"]
    list_filter_submit = True

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": ("id", "name", "description", "status", "created_by"),
                "classes": ["tab"],
            },
        ),
        (
            "Devices & PLCs",
            {
                "fields": ("devices", "plcs"),
                "classes": ["tab"],
            },
        ),
        (
            "Scheduling",
            {
                "fields": ("scheduled_start", "scheduled_stop", "duration_seconds"),
                "classes": ["tab"],
            },
        ),
        (
            "Scenario Configuration",
            {
                "fields": ("scenario",),
                "classes": ["tab"],
            },
        ),
        (
            "Execution",
            {
                "fields": ("started_at", "stopped_at"),
                "classes": ["tab"],
            },
        ),
        (
            "Statistics",
            {
                "fields": (
                    "messages_sent",
                    "events_generated",
                    "faults_injected",
                    "error_count",
                    "last_error",
                ),
                "classes": ["tab"],
            },
        ),
    )

    actions_detail = ["start_session", "stop_session", "pause_session"]
    actions = ["start_sessions", "stop_sessions", "pause_sessions"]

    @display(description="Status", label=True)
    def status_display(self, obj):
        colors = {
            "pending": "secondary",
            "running": "success",
            "paused": "warning",
            "stopped": "info",
            "failed": "danger",
        }
        return obj.status.upper(), colors.get(obj.status, "secondary")

    @display(description="Devices")
    def device_count(self, obj):
        return obj.devices.count()

    @display(description="PLCs")
    def plc_count(self, obj):
        return obj.plcs.count()

    @display(description="Duration")
    def duration_display(self, obj):
        if obj.started_at and obj.stopped_at:
            delta = obj.stopped_at - obj.started_at
            return str(delta).split(".")[0]
        elif obj.started_at:
            delta = timezone.now() - obj.started_at
            return f"{str(delta).split('.')[0]} (running)"
        return "-"

    @action(description="Start session")
    def start_session(self, request, object_id):
        session = SimulationSession.objects.get(pk=object_id)
        session.start()

    @action(description="Stop session")
    def stop_session(self, request, object_id):
        session = SimulationSession.objects.get(pk=object_id)
        session.stop()

    @action(description="Pause session")
    def pause_session(self, request, object_id):
        session = SimulationSession.objects.get(pk=object_id)
        session.pause()

    @admin.action(description="Start selected sessions")
    def start_sessions(self, request, queryset):
        for session in queryset:
            session.start()
        self.message_user(request, f"Started {queryset.count()} sessions.")

    @admin.action(description="Stop selected sessions")
    def stop_sessions(self, request, queryset):
        for session in queryset:
            session.stop()
        self.message_user(request, f"Stopped {queryset.count()} sessions.")

    @admin.action(description="Pause selected sessions")
    def pause_sessions(self, request, queryset):
        for session in queryset:
            session.pause()
        self.message_user(request, f"Paused {queryset.count()} sessions.")


@admin.register(SimulationEvent)
class SimulationEventAdmin(ModelAdmin):
    """Admin for simulation events with Unfold styling."""

    list_display = [
        "created_at",
        "event_type_display",
        "severity_display",
        "device",
        "value_display",
        "acknowledged_display",
    ]
    list_filter = [
        ("event_type", ChoicesDropdownFilter),
        ("severity", ChoicesDropdownFilter),
        "acknowledged",
        ("created_at", RangeDateTimeFilter),
    ]
    search_fields = ["message", "device__device_id", "plc__name"]
    readonly_fields = ["id", "created_at", "published_at"]
    date_hierarchy = "created_at"
    list_filter_submit = True
    list_per_page = 50

    fieldsets = (
        (
            "Event Details",
            {
                "fields": ("id", "event_type", "severity", "message"),
                "classes": ["tab"],
            },
        ),
        (
            "Source",
            {
                "fields": ("device", "plc", "session"),
                "classes": ["tab"],
            },
        ),
        (
            "Values",
            {
                "fields": ("value", "threshold"),
                "classes": ["tab"],
            },
        ),
        (
            "Acknowledgement",
            {
                "fields": ("acknowledged", "acknowledged_by", "acknowledged_at"),
                "classes": ["tab"],
            },
        ),
        (
            "Publishing",
            {
                "fields": ("published_to_mqtt", "published_at"),
                "classes": ["tab"],
            },
        ),
    )

    actions_detail = ["acknowledge_event", "unacknowledge_event"]
    actions = ["acknowledge_events", "unacknowledge_events"]

    @display(description="Event Type", label=True)
    def event_type_display(self, obj):
        colors = {
            "threshold_high": "warning",
            "threshold_low": "warning",
            "critical_high": "danger",
            "critical_low": "danger",
            "device_fault": "danger",
            "device_recovery": "success",
            "plc_offline": "danger",
            "plc_online": "success",
            "rate_of_change": "warning",
        }
        return obj.get_event_type_display(), colors.get(obj.event_type, "secondary")

    @display(description="Severity", label=True)
    def severity_display(self, obj):
        colors = {
            "critical": "danger",
            "high": "warning",
            "medium": "info",
            "low": "primary",
            "info": "secondary",
        }
        return obj.severity.upper(), colors.get(obj.severity, "secondary")

    @display(description="Value")
    def value_display(self, obj):
        if obj.value is None:
            return "-"
        if obj.threshold:
            return f"{obj.value:.2f} (threshold: {obj.threshold:.2f})"
        return f"{obj.value:.2f}"

    @display(description="Acknowledged", boolean=True)
    def acknowledged_display(self, obj):
        return obj.acknowledged

    @action(description="Acknowledge")
    def acknowledge_event(self, request, object_id):
        event = SimulationEvent.objects.get(pk=object_id)
        event.acknowledged = True
        event.acknowledged_by = (
            request.user.username if hasattr(request, "user") else "admin"
        )
        event.acknowledged_at = timezone.now()
        event.save()

    @action(description="Unacknowledge")
    def unacknowledge_event(self, request, object_id):
        event = SimulationEvent.objects.get(pk=object_id)
        event.acknowledged = False
        event.acknowledged_by = ""
        event.acknowledged_at = None
        event.save()

    @admin.action(description="Acknowledge selected events")
    def acknowledge_events(self, request, queryset):
        count = queryset.filter(acknowledged=False).update(
            acknowledged=True,
            acknowledged_by=(
                request.user.username if hasattr(request, "user") else "admin"
            ),
            acknowledged_at=timezone.now(),
        )
        self.message_user(request, f"Acknowledged {count} events.")

    @admin.action(description="Unacknowledge selected events")
    def unacknowledge_events(self, request, queryset):
        count = queryset.update(
            acknowledged=False, acknowledged_by="", acknowledged_at=None
        )
        self.message_user(request, f"Unacknowledged {count} events.")
