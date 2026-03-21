"""REST API views for steel plant assets."""

import logging

from django.db.models import Count, Q
from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from .models import Area, Cell, Device, DeviceType, Line, MaintenanceRecord, Plant
from .serializers import (
    AreaMinimalSerializer,
    AreaSerializer,
    CellMinimalSerializer,
    CellSerializer,
    DeviceCreateSerializer,
    DeviceMinimalSerializer,
    DeviceSearchSerializer,
    DeviceSerializer,
    DeviceStatusSerializer,
    DeviceThresholdsSerializer,
    DeviceTypeMinimalSerializer,
    DeviceTypeSerializer,
    LineMinimalSerializer,
    LineSerializer,
    MaintenanceRecordCreateSerializer,
    MaintenanceRecordSerializer,
    PlantMinimalSerializer,
    PlantSerializer,
)

logger = logging.getLogger(__name__)


# ============================================
# Plant ViewSet
# ============================================


class PlantViewSet(viewsets.ModelViewSet):
    """
    ViewSet for plant management.

    Provides CRUD operations for plants.
    """

    queryset = Plant.objects.all()
    serializer_class = PlantSerializer
    lookup_field = "code"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return PlantMinimalSerializer
        return PlantSerializer

    @action(detail=True, methods=["get"])
    def hierarchy(self, request, code=None):
        """Get complete hierarchy for a plant."""
        plant = self.get_object()

        # Count statistics
        areas = plant.areas.all()
        total_lines = Line.objects.filter(area__plant=plant).count()
        total_cells = Cell.objects.filter(line__area__plant=plant).count()
        devices = Device.objects.filter(cell__line__area__plant=plant)
        total_devices = devices.count()
        devices_online = devices.filter(status="online").count()
        devices_offline = devices.filter(status="offline").count()
        devices_fault = devices.filter(status="fault").count()

        data = {
            "plant": PlantSerializer(plant).data,
            "total_areas": areas.count(),
            "total_lines": total_lines,
            "total_cells": total_cells,
            "total_devices": total_devices,
            "devices_online": devices_online,
            "devices_offline": devices_offline,
            "devices_fault": devices_fault,
        }

        return Response(data)

    @action(detail=True, methods=["get"])
    def devices(self, request, code=None):
        """Get all devices in a plant."""
        plant = self.get_object()
        devices = Device.objects.filter(cell__line__area__plant=plant).select_related(
            "device_type", "cell__line__area"
        )

        # Apply filters
        status_filter = request.query_params.get("status")
        if status_filter:
            devices = devices.filter(status=status_filter)

        active_filter = request.query_params.get("is_active")
        if active_filter is not None:
            devices = devices.filter(is_active=active_filter.lower() == "true")

        serializer = DeviceMinimalSerializer(devices, many=True)
        return Response(
            {"plant": plant.code, "count": devices.count(), "devices": serializer.data}
        )


# ============================================
# Area ViewSet
# ============================================


class AreaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for area management.
    """

    queryset = Area.objects.select_related("plant").all()
    serializer_class = AreaSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["plant", "area_type", "is_active"]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["sequence", "name", "created_at"]
    ordering = ["sequence", "name"]

    def get_serializer_class(self):
        if self.action == "list":
            return AreaMinimalSerializer
        return AreaSerializer

    @action(detail=True, methods=["get"])
    def devices(self, request, pk=None):
        """Get all devices in an area."""
        area = self.get_object()
        devices = Device.objects.filter(cell__line__area=area).select_related(
            "device_type", "cell__line"
        )

        serializer = DeviceMinimalSerializer(devices, many=True)
        return Response(
            {"area": area.code, "count": devices.count(), "devices": serializer.data}
        )

    @action(detail=True, methods=["get"])
    def status_summary(self, request, pk=None):
        """Get device status summary for an area."""
        area = self.get_object()
        devices = Device.objects.filter(cell__line__area=area)

        summary = devices.values("status").annotate(count=Count("id"))
        by_type = devices.values("device_type__code").annotate(count=Count("id"))

        return Response(
            {
                "area": area.code,
                "total_devices": devices.count(),
                "by_status": {item["status"]: item["count"] for item in summary},
                "by_type": {
                    item["device_type__code"]: item["count"] for item in by_type
                },
            }
        )


# ============================================
# Line ViewSet
# ============================================


class LineViewSet(viewsets.ModelViewSet):
    """
    ViewSet for line management.
    """

    queryset = Line.objects.select_related("area__plant").all()
    serializer_class = LineSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["area", "is_active"]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["code"]

    def get_serializer_class(self):
        if self.action == "list":
            return LineMinimalSerializer
        return LineSerializer


# ============================================
# Cell ViewSet
# ============================================


class CellViewSet(viewsets.ModelViewSet):
    """
    ViewSet for cell management.
    """

    queryset = Cell.objects.select_related("line__area__plant").all()
    serializer_class = CellSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["line", "is_active"]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["code", "name", "created_at"]
    ordering = ["code"]

    def get_serializer_class(self):
        if self.action == "list":
            return CellMinimalSerializer
        return CellSerializer


# ============================================
# Device Type ViewSet
# ============================================


class DeviceTypeViewSet(viewsets.ModelViewSet):
    """
    ViewSet for device type management.
    """

    queryset = DeviceType.objects.all()
    serializer_class = DeviceTypeSerializer
    lookup_field = "code"
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["code", "name", "description"]
    ordering_fields = ["name", "created_at"]
    ordering = ["name"]

    def get_serializer_class(self):
        if self.action == "list":
            return DeviceTypeMinimalSerializer
        return DeviceTypeSerializer


# ============================================
# Device ViewSet
# ============================================


class DeviceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for device management.

    Provides CRUD operations plus status updates,
    threshold management, and maintenance records.
    """

    queryset = Device.objects.select_related(
        "device_type", "cell__line__area__plant"
    ).all()
    serializer_class = DeviceSerializer
    lookup_field = "device_id"
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["status", "is_active", "device_type", "cell__line__area"]
    search_fields = ["device_id", "name", "description", "serial_number"]
    ordering_fields = ["device_id", "name", "status", "last_seen", "created_at"]
    ordering = ["device_id"]

    def get_serializer_class(self):
        if self.action == "list":
            return DeviceMinimalSerializer
        elif self.action == "create":
            return DeviceCreateSerializer
        return DeviceSerializer

    @action(detail=True, methods=["patch"])
    def update_status(self, request, device_id=None):
        """Update device status."""
        device = self.get_object()
        serializer = DeviceStatusSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        device.update_status(serializer.validated_data["status"])

        return Response(
            {
                "device_id": device.device_id,
                "status": device.status,
                "last_seen": device.last_seen.isoformat() if device.last_seen else None,
            }
        )

    @action(detail=True, methods=["patch"])
    def update_thresholds(self, request, device_id=None):
        """Update device thresholds."""
        device = self.get_object()
        serializer = DeviceThresholdsSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        for field, value in serializer.validated_data.items():
            setattr(device, field, value)
        device.save()

        return Response(
            {
                "device_id": device.device_id,
                "warning_low": device.warning_low,
                "warning_high": device.warning_high,
                "critical_low": device.critical_low,
                "critical_high": device.critical_high,
            }
        )

    @action(detail=True, methods=["get", "post"])
    def maintenance(self, request, device_id=None):
        """Get or create maintenance records for a device."""
        device = self.get_object()

        if request.method == "GET":
            records = device.maintenance_records.all()[:10]
            serializer = MaintenanceRecordSerializer(records, many=True)
            return Response(
                {
                    "device_id": device.device_id,
                    "count": device.maintenance_records.count(),
                    "records": serializer.data,
                }
            )

        elif request.method == "POST":
            serializer = MaintenanceRecordCreateSerializer(
                data={**request.data, "device": device.id}
            )
            serializer.is_valid(raise_exception=True)
            record = serializer.save()

            return Response(
                MaintenanceRecordSerializer(record).data, status=status.HTTP_201_CREATED
            )

    @action(detail=False, methods=["get"])
    def by_area(self, request):
        """Get devices grouped by area."""
        area_code = request.query_params.get("area")
        if not area_code:
            return Response(
                {"error": "area parameter required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            area = Area.objects.get(code=area_code)
        except Area.DoesNotExist:
            return Response(
                {"error": f"Area {area_code} not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        devices = Device.objects.filter(cell__line__area=area).select_related(
            "device_type"
        )

        serializer = DeviceMinimalSerializer(devices, many=True)
        return Response(
            {"area": area_code, "count": devices.count(), "devices": serializer.data}
        )

    @action(detail=False, methods=["post"])
    def search(self, request):
        """Advanced device search."""
        serializer = DeviceSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        devices = Device.objects.select_related("device_type", "cell__line__area")

        # Apply filters
        if params.get("query"):
            query = params["query"]
            devices = devices.filter(
                Q(device_id__icontains=query)
                | Q(name__icontains=query)
                | Q(description__icontains=query)
            )

        if params.get("area"):
            devices = devices.filter(cell__line__area__code=params["area"])

        if params.get("device_type"):
            devices = devices.filter(device_type__code=params["device_type"])

        if params.get("status"):
            devices = devices.filter(status=params["status"])

        if "is_active" in params:
            devices = devices.filter(is_active=params["is_active"])

        if params.get("tags"):
            for tag in params["tags"]:
                devices = devices.filter(tags__contains=[tag])

        serializer = DeviceMinimalSerializer(devices[:100], many=True)
        return Response({"count": devices.count(), "devices": serializer.data})

    @action(detail=False, methods=["get"])
    def status_summary(self, request):
        """Get overall device status summary."""
        devices = Device.objects.all()

        by_status = devices.values("status").annotate(count=Count("id"))
        by_type = devices.values("device_type__code").annotate(count=Count("id"))
        by_area = devices.values("cell__line__area__code").annotate(count=Count("id"))

        return Response(
            {
                "total": devices.count(),
                "active": devices.filter(is_active=True).count(),
                "by_status": {item["status"]: item["count"] for item in by_status},
                "by_type": {
                    item["device_type__code"]: item["count"] for item in by_type
                },
                "by_area": {
                    item["cell__line__area__code"]: item["count"] for item in by_area
                },
            }
        )


# ============================================
# Maintenance Record ViewSet
# ============================================


class MaintenanceRecordViewSet(viewsets.ModelViewSet):
    """
    ViewSet for maintenance record management.
    """

    queryset = MaintenanceRecord.objects.select_related("device").all()
    serializer_class = MaintenanceRecordSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["device", "maintenance_type"]
    search_fields = ["description", "performed_by", "device__device_id"]
    ordering_fields = ["performed_at", "created_at"]
    ordering = ["-performed_at"]

    def get_serializer_class(self):
        if self.action == "create":
            return MaintenanceRecordCreateSerializer
        return MaintenanceRecordSerializer


# ============================================
# Asset Dashboard View
# ============================================


class AssetDashboardView(APIView):
    """
    Dashboard endpoint for asset overview.
    """

    def get(self, request):
        """Get asset dashboard data."""
        plants = Plant.objects.filter(is_active=True)
        devices = Device.objects.all()

        # Status counts
        status_counts = devices.values("status").annotate(count=Count("id"))

        # Area summaries
        areas = Area.objects.filter(is_active=True).select_related("plant")
        area_summaries = []
        for area in areas:
            area_devices = devices.filter(cell__line__area=area)
            area_summaries.append(
                {
                    "code": area.code,
                    "name": area.name,
                    "total_devices": area_devices.count(),
                    "online": area_devices.filter(status="online").count(),
                    "offline": area_devices.filter(status="offline").count(),
                    "fault": area_devices.filter(status="fault").count(),
                }
            )

        # Maintenance due
        from datetime import timedelta

        from django.utils import timezone

        upcoming_maintenance = Device.objects.filter(
            next_calibration__lte=timezone.now().date() + timedelta(days=30),
            next_calibration__isnull=False,
        ).count()

        return Response(
            {
                "summary": {
                    "total_plants": plants.count(),
                    "total_areas": Area.objects.filter(is_active=True).count(),
                    "total_devices": devices.count(),
                    "active_devices": devices.filter(is_active=True).count(),
                },
                "by_status": {item["status"]: item["count"] for item in status_counts},
                "areas": area_summaries,
                "maintenance_due": upcoming_maintenance,
            }
        )
