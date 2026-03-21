"""REST API views for steel plant simulator."""

from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import (
    DeviceProfile,
    SimulatedDevice,
    SimulatedPLC,
    SimulationEvent,
    SimulationSession,
)
from .serializers import (
    AreaSummarySerializer,
    BulkDeviceControlSerializer,
    BulkFaultInjectionSerializer,
    DeviceControlSerializer,
    DeviceFaultSerializer,
    DeviceProfileSerializer,
    DeviceValueSerializer,
    EventAcknowledgeSerializer,
    PLCControlSerializer,
    SessionControlSerializer,
    SimulatedDeviceSerializer,
    SimulatedPLCSerializer,
    SimulationEventSerializer,
    SimulationSessionSerializer,
)


class DeviceProfileViewSet(viewsets.ModelViewSet):
    """
    ViewSet for device profile templates.

    list: Get all device profiles
    retrieve: Get a specific profile
    create: Create a new profile template
    update: Update a profile
    delete: Delete a profile (only if no devices use it)
    """

    queryset = DeviceProfile.objects.all()
    serializer_class = DeviceProfileSerializer
    search_fields = ["name", "description", "sensor_type"]
    filterset_fields = ["sensor_type"]
    ordering_fields = ["name", "sensor_type", "created_at"]
    ordering = ["sensor_type", "name"]


class SimulatedPLCViewSet(viewsets.ModelViewSet):
    """
    ViewSet for simulated PLCs.

    Includes actions for controlling PLC simulation state.
    """

    queryset = SimulatedPLC.objects.prefetch_related("devices").all()
    serializer_class = SimulatedPLCSerializer
    search_fields = ["name", "description", "line", "cell"]
    filterset_fields = ["plc_type", "area", "is_online", "is_simulating"]
    ordering_fields = ["name", "area", "line", "created_at"]
    ordering = ["area", "line", "name"]

    @action(detail=True, methods=["post"])
    def control(self, request, pk=None):
        """Control PLC state: start, stop, online, offline."""
        plc = self.get_object()
        serializer = PLCControlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_name = serializer.validated_data["action"]

        if action_name == "start":
            plc.is_simulating = True
            plc.is_online = True
            plc.last_heartbeat = timezone.now()
            # Start all devices
            plc.devices.update(status="running", quality="good")
        elif action_name == "stop":
            plc.is_simulating = False
            # Stop all devices
            plc.devices.update(status="offline")
        elif action_name == "online":
            plc.is_online = True
            plc.last_heartbeat = timezone.now()
        elif action_name == "offline":
            plc.is_online = False
            plc.is_simulating = False
            plc.devices.update(status="offline")

        plc.save()
        return Response(SimulatedPLCSerializer(plc).data)

    @action(detail=True, methods=["get"])
    def devices(self, request, pk=None):
        """Get all devices for this PLC."""
        plc = self.get_object()
        devices = plc.devices.all()
        serializer = SimulatedDeviceSerializer(devices, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def bulk_control(self, request):
        """Control multiple PLCs at once."""
        plc_ids = request.data.get("plc_ids", [])
        action_name = request.data.get("action")

        if not plc_ids or not action_name:
            return Response(
                {"error": "plc_ids and action are required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        plcs = SimulatedPLC.objects.filter(id__in=plc_ids)

        if action_name == "start":
            plcs.update(
                is_simulating=True, is_online=True, last_heartbeat=timezone.now()
            )
            SimulatedDevice.objects.filter(plc__in=plcs).update(
                status="running", quality="good"
            )
        elif action_name == "stop":
            plcs.update(is_simulating=False)
            SimulatedDevice.objects.filter(plc__in=plcs).update(status="offline")
        elif action_name == "online":
            plcs.update(is_online=True, last_heartbeat=timezone.now())
        elif action_name == "offline":
            plcs.update(is_online=False, is_simulating=False)
            SimulatedDevice.objects.filter(plc__in=plcs).update(status="offline")

        return Response({"updated": plcs.count()})


class SimulatedDeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for simulated devices.

    Includes actions for controlling device state and injecting faults.
    """

    queryset = SimulatedDevice.objects.select_related("plc", "profile").all()
    serializer_class = SimulatedDeviceSerializer
    search_fields = ["device_id", "name", "description"]
    filterset_fields = [
        "status",
        "quality",
        "fault_type",
        "simulation_mode",
        "plc",
        "plc__area",
    ]
    ordering_fields = ["device_id", "name", "status", "created_at"]
    ordering = ["plc", "device_id"]

    @action(detail=True, methods=["post"])
    def control(self, request, pk=None):
        """Control device state: start, stop, restart."""
        device = self.get_object()
        serializer = DeviceControlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_name = serializer.validated_data["action"]

        if action_name == "start":
            device.status = "running"
            device.quality = "good"
            device.fault_type = "none"
        elif action_name == "stop":
            device.status = "offline"
        elif action_name == "restart":
            device.status = "running"
            device.quality = "good"
            device.fault_type = "none"
            device.sequence_number = 0
            device.error_count = 0

        device.save()
        return Response(SimulatedDeviceSerializer(device).data)

    @action(detail=True, methods=["post"])
    def inject_fault(self, request, pk=None):
        """Inject a fault into the device."""
        device = self.get_object()
        serializer = DeviceFaultSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        fault_type = serializer.validated_data["fault_type"]
        duration = serializer.validated_data.get("duration_seconds")

        device.fault_type = fault_type
        device.fault_start = timezone.now()

        if duration:
            from datetime import timedelta

            device.fault_end = timezone.now() + timedelta(seconds=duration)

        if fault_type == "none":
            device.fault_end = timezone.now()
            device.quality = "good"
        elif fault_type in ["stuck", "dead"]:
            device.quality = "bad"
        else:
            device.quality = "uncertain"

        device.save()

        # Create fault event
        SimulationEvent.objects.create(
            device=device,
            plc=device.plc,
            event_type="device_fault" if fault_type != "none" else "device_recovery",
            severity="high" if fault_type != "none" else "info",
            message=(
                f"Fault injected: {fault_type}"
                if fault_type != "none"
                else "Device recovered from fault"
            ),
            value=device.current_value,
        )

        return Response(SimulatedDeviceSerializer(device).data)

    @action(detail=True, methods=["post"])
    def set_value(self, request, pk=None):
        """Manually set device value or target."""
        device = self.get_object()
        serializer = DeviceValueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if "value" in serializer.validated_data:
            device.current_value = serializer.validated_data["value"]
            device.last_value_change_at = timezone.now()
        if "target_value" in serializer.validated_data:
            device.target_value = serializer.validated_data["target_value"]
        if "quality" in serializer.validated_data:
            device.quality = serializer.validated_data["quality"]

        device.save()
        return Response(SimulatedDeviceSerializer(device).data)

    @action(detail=False, methods=["post"])
    def bulk_control(self, request):
        """Control multiple devices at once."""
        serializer = BulkDeviceControlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_ids = serializer.validated_data["device_ids"]
        action_name = serializer.validated_data["action"]

        devices = SimulatedDevice.objects.filter(id__in=device_ids)

        if action_name == "start":
            devices.update(status="running", quality="good")
        elif action_name == "stop":
            devices.update(status="offline")
        elif action_name == "restart":
            devices.update(
                status="running",
                quality="good",
                fault_type="none",
                sequence_number=0,
                error_count=0,
            )

        return Response({"updated": devices.count()})

    @action(detail=False, methods=["post"])
    def bulk_inject_fault(self, request):
        """Inject faults into multiple devices."""
        serializer = BulkFaultInjectionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device_ids = serializer.validated_data["device_ids"]
        fault_type = serializer.validated_data["fault_type"]
        duration = serializer.validated_data.get("duration_seconds")

        devices = SimulatedDevice.objects.filter(id__in=device_ids)

        update_fields = {
            "fault_type": fault_type,
            "fault_start": timezone.now(),
        }

        if fault_type == "none":
            update_fields["fault_end"] = timezone.now()
            update_fields["quality"] = "good"
        elif fault_type in ["stuck", "dead"]:
            update_fields["quality"] = "bad"
        else:
            update_fields["quality"] = "uncertain"

        if duration:
            from datetime import timedelta

            update_fields["fault_end"] = timezone.now() + timedelta(seconds=duration)

        devices.update(**update_fields)

        return Response({"updated": devices.count()})


class SimulationSessionViewSet(viewsets.ModelViewSet):
    """
    ViewSet for simulation sessions.

    Manage grouped simulation runs with start/stop/pause controls.
    """

    queryset = SimulationSession.objects.prefetch_related("devices", "plcs").all()
    serializer_class = SimulationSessionSerializer
    search_fields = ["name", "description"]
    filterset_fields = ["status"]
    ordering_fields = ["name", "status", "created_at", "started_at"]
    ordering = ["-created_at"]

    def perform_create(self, serializer):
        serializer.save(
            created_by=self.request.user.email if hasattr(self.request, "user") else ""
        )

    @action(detail=True, methods=["post"])
    def control(self, request, pk=None):
        """Control session: start, stop, pause, resume."""
        session = self.get_object()
        serializer = SessionControlSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        action_name = serializer.validated_data["action"]

        if action_name == "start":
            session.start()
            # Start all associated devices
            session.devices.update(status="running", quality="good")
            for plc in session.plcs.all():
                plc.devices.update(status="running", quality="good")
                plc.is_simulating = True
                plc.is_online = True
                plc.save()
        elif action_name == "stop":
            session.stop()
            session.devices.update(status="offline")
            for plc in session.plcs.all():
                plc.devices.update(status="offline")
                plc.is_simulating = False
                plc.save()
        elif action_name == "pause":
            session.pause()
        elif action_name == "resume":
            session.status = "running"
            session.save()

        return Response(SimulationSessionSerializer(session).data)

    @action(detail=True, methods=["get"])
    def events(self, request, pk=None):
        """Get events for this session."""
        session = self.get_object()
        events = session.events.all()[:100]
        serializer = SimulationEventSerializer(events, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def stats(self, request, pk=None):
        """Get statistics for this session."""
        session = self.get_object()

        device_stats = session.devices.aggregate(
            total=Count("id"),
            running=Count("id", filter=Q(status="running")),
            faulted=Count("id", filter=~Q(fault_type="none")),
            messages=Sum("messages_sent"),
        )

        event_stats = session.events.aggregate(
            total=Count("id"),
            critical=Count("id", filter=Q(severity="critical")),
            unacknowledged=Count("id", filter=Q(acknowledged=False)),
        )

        return Response(
            {
                "session_id": str(session.id),
                "status": session.status,
                "duration": (
                    str(session.stopped_at - session.started_at).split(".")[0]
                    if session.stopped_at
                    else None
                ),
                "devices": device_stats,
                "events": event_stats,
                "messages_sent": session.messages_sent,
            }
        )


class SimulationEventViewSet(viewsets.ModelViewSet):
    """
    ViewSet for simulation events.

    View and acknowledge events generated during simulation.
    """

    queryset = SimulationEvent.objects.select_related("device", "plc", "session").all()
    serializer_class = SimulationEventSerializer
    search_fields = ["message", "device__device_id", "plc__name"]
    filterset_fields = [
        "event_type",
        "severity",
        "acknowledged",
        "device",
        "plc",
        "session",
    ]
    ordering_fields = ["created_at", "severity"]
    ordering = ["-created_at"]

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        """Acknowledge an event."""
        event = self.get_object()
        serializer = EventAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        event.acknowledged = True
        event.acknowledged_by = serializer.validated_data.get(
            "acknowledged_by",
            request.user.email if hasattr(request, "user") else "unknown",
        )
        event.acknowledged_at = timezone.now()
        event.save()

        return Response(SimulationEventSerializer(event).data)

    @action(detail=False, methods=["post"])
    def bulk_acknowledge(self, request):
        """Acknowledge multiple events."""
        event_ids = request.data.get("event_ids", [])
        acknowledged_by = request.data.get(
            "acknowledged_by",
            request.user.email if hasattr(request, "user") else "unknown",
        )

        count = SimulationEvent.objects.filter(
            id__in=event_ids, acknowledged=False
        ).update(
            acknowledged=True,
            acknowledged_by=acknowledged_by,
            acknowledged_at=timezone.now(),
        )

        return Response({"acknowledged": count})

    @action(detail=False, methods=["get"])
    def unacknowledged(self, request):
        """Get all unacknowledged events."""
        events = self.queryset.filter(acknowledged=False)
        serializer = SimulationEventSerializer(events[:100], many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_severity(self, request):
        """Get events grouped by severity."""
        severity = request.query_params.get("severity", "critical")
        events = self.queryset.filter(severity=severity)
        serializer = SimulationEventSerializer(events[:100], many=True)
        return Response(serializer.data)


class SimulatorDashboardViewSet(viewsets.ViewSet):
    """
    Dashboard endpoints for simulator overview.

    Provides aggregated statistics and summaries.
    """

    @action(detail=False, methods=["get"])
    def overview(self, request):
        """Get overall simulator status."""
        plc_stats = SimulatedPLC.objects.aggregate(
            total=Count("id"),
            online=Count("id", filter=Q(is_online=True)),
            simulating=Count("id", filter=Q(is_simulating=True)),
        )

        device_stats = SimulatedDevice.objects.aggregate(
            total=Count("id"),
            running=Count("id", filter=Q(status="running")),
            fault=Count("id", filter=~Q(fault_type="none")),
        )

        session_stats = SimulationSession.objects.filter(status="running").count()

        total_messages = (
            SimulatedDevice.objects.aggregate(total=Sum("messages_sent"))["total"] or 0
        )

        unacknowledged = SimulationEvent.objects.filter(acknowledged=False).count()

        # Devices by area
        devices_by_area = {}
        for area in SimulatedPLC.Area.choices:
            count = SimulatedDevice.objects.filter(plc__area=area[0]).count()
            devices_by_area[area[0]] = count

        # Devices by status
        devices_by_status = {}
        for status_choice in SimulatedDevice.Status.choices:
            count = SimulatedDevice.objects.filter(status=status_choice[0]).count()
            devices_by_status[status_choice[0]] = count

        # Recent events
        recent_events = SimulationEvent.objects.all()[:10]

        data = {
            "total_plcs": plc_stats["total"],
            "online_plcs": plc_stats["online"],
            "simulating_plcs": plc_stats["simulating"],
            "total_devices": device_stats["total"],
            "running_devices": device_stats["running"],
            "fault_devices": device_stats["fault"],
            "active_sessions": session_stats,
            "total_messages_sent": total_messages,
            "unacknowledged_events": unacknowledged,
            "devices_by_area": devices_by_area,
            "devices_by_status": devices_by_status,
            "recent_events": SimulationEventSerializer(recent_events, many=True).data,
        }

        return Response(data)

    @action(detail=False, methods=["get"])
    def areas(self, request):
        """Get summary by area."""
        summaries = []

        for area_code, area_display in SimulatedPLC.Area.choices:
            plcs = SimulatedPLC.objects.filter(area=area_code)
            devices = SimulatedDevice.objects.filter(plc__area=area_code)

            summary = {
                "area": area_code,
                "area_display": area_display,
                "plc_count": plcs.count(),
                "device_count": devices.count(),
                "running_count": devices.filter(status="running").count(),
                "fault_count": devices.exclude(fault_type="none").count(),
                "avg_value": devices.filter(current_value__isnull=False).aggregate(
                    avg=Avg("current_value")
                )["avg"],
            }
            summaries.append(summary)

        serializer = AreaSummarySerializer(summaries, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def live_values(self, request):
        """Get current values for all running devices."""
        devices = (
            SimulatedDevice.objects.filter(status="running")
            .select_related("plc", "profile")
            .values(
                "id",
                "device_id",
                "name",
                "current_value",
                "quality",
                "last_published_at",
                "plc__area",
                "plc__line",
                "profile__unit",
                "profile__sensor_type",
            )
        )

        return Response(list(devices))

    @action(detail=False, methods=["post"])
    def start_all(self, request):
        """Start simulation for all PLCs and devices."""
        plc_count = SimulatedPLC.objects.update(
            is_simulating=True, is_online=True, last_heartbeat=timezone.now()
        )
        device_count = SimulatedDevice.objects.update(status="running", quality="good")

        return Response({"plcs_started": plc_count, "devices_started": device_count})

    @action(detail=False, methods=["post"])
    def stop_all(self, request):
        """Stop simulation for all PLCs and devices."""
        plc_count = SimulatedPLC.objects.update(is_simulating=False)
        device_count = SimulatedDevice.objects.update(status="offline")

        # Stop all running sessions
        SimulationSession.objects.filter(status="running").update(
            status="stopped", stopped_at=timezone.now()
        )

        return Response({"plcs_stopped": plc_count, "devices_stopped": device_count})

    @action(detail=False, methods=["post"])
    def reset(self, request):
        """Reset all simulation state."""
        # Reset devices
        SimulatedDevice.objects.update(
            status="offline",
            current_value=None,
            target_value=None,
            quality="good",
            fault_type="none",
            fault_start=None,
            fault_end=None,
            sequence_number=0,
            messages_sent=0,
            error_count=0,
            last_error="",
            last_published_at=None,
            last_value_change_at=None,
        )

        # Reset PLCs
        SimulatedPLC.objects.update(
            is_online=False, is_simulating=False, last_heartbeat=None
        )

        # Stop sessions
        SimulationSession.objects.filter(status__in=["running", "paused"]).update(
            status="stopped", stopped_at=timezone.now()
        )

        return Response({"status": "reset complete"})
