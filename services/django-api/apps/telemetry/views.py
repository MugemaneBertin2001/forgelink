"""REST API views for telemetry data."""

import logging

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import (
    AnomalyDetectionSerializer,
    AreaOverviewSerializer,
    BatchTelemetrySerializer,
    DeviceCompareSerializer,
    DeviceStatisticsSerializer,
    TelemetryEventSerializer,
    TelemetryQuerySerializer,
)
from .services import AggregationInterval, TelemetryService, TimeRange
from .tdengine import init_tdengine_schema

logger = logging.getLogger(__name__)


class TelemetryViewSet(viewsets.ViewSet):
    """
    ViewSet for telemetry data operations.

    Provides endpoints for:
    - Querying device history
    - Getting latest values
    - Batch recording
    - Statistics
    """

    @action(
        detail=False, methods=["get"], url_path="device/(?P<device_id>[^/.]+)/history"
    )
    def device_history(self, request, device_id=None):
        """
        Get historical telemetry for a device.

        Query parameters:
        - start_time: ISO datetime
        - end_time: ISO datetime
        - time_range: 1h, 6h, 24h, 7d, 30d (alternative to start/end)
        - interval: raw, 1m, 5m, 15m, 1h, 1d
        - limit: max records (default 10000)
        """
        serializer = TelemetryQuerySerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        # Parse time range
        time_range = None
        if params.get("time_range"):
            time_range_map = {
                "1h": TimeRange.LAST_HOUR,
                "6h": TimeRange.LAST_6_HOURS,
                "24h": TimeRange.LAST_24_HOURS,
                "7d": TimeRange.LAST_7_DAYS,
                "30d": TimeRange.LAST_30_DAYS,
            }
            time_range = time_range_map.get(params["time_range"])

        # Parse interval
        interval = None
        if params.get("interval") and params["interval"] != "raw":
            interval_map = {
                "1m": AggregationInterval.ONE_MINUTE,
                "5m": AggregationInterval.FIVE_MINUTES,
                "15m": AggregationInterval.FIFTEEN_MINUTES,
                "1h": AggregationInterval.ONE_HOUR,
                "1d": AggregationInterval.ONE_DAY,
            }
            interval = interval_map.get(params["interval"])

        try:
            data = TelemetryService.get_device_history(
                device_id=device_id,
                start_time=params.get("start_time"),
                end_time=params.get("end_time"),
                time_range=time_range,
                interval=interval,
                limit=params.get("limit", 10000),
            )

            return Response({"device_id": device_id, "count": len(data), "data": data})

        except Exception as e:
            logger.error(f"Error querying device history: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False, methods=["get"], url_path="device/(?P<device_id>[^/.]+)/latest"
    )
    def device_latest(self, request, device_id=None):
        """Get the latest value for a device."""
        try:
            data = TelemetryService.get_latest_value(device_id)

            if data:
                return Response(data)
            else:
                return Response(
                    {"error": "No data found for device"},
                    status=status.HTTP_404_NOT_FOUND,
                )

        except Exception as e:
            logger.error(f"Error querying latest value: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False, methods=["get"], url_path="device/(?P<device_id>[^/.]+)/stats"
    )
    def device_stats(self, request, device_id=None):
        """
        Get statistics for a device.

        Query parameters:
        - period: 1h, 6h, 24h, 7d, 30d (default 24h)
        """
        period = request.query_params.get("period", "24h")

        try:
            data = TelemetryService.get_device_statistics(
                device_id=device_id, period=period
            )

            serializer = DeviceStatisticsSerializer(data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error querying device stats: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(
        detail=False, methods=["get"], url_path="device/(?P<device_id>[^/.]+)/anomalies"
    )
    def device_anomalies(self, request, device_id=None):
        """
        Detect anomalies for a device.

        Query parameters:
        - period: 1h, 6h, 24h, 7d (default 24h)
        - std_threshold: standard deviations (default 3.0)
        """
        serializer = AnomalyDetectionSerializer(data=request.query_params)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        try:
            anomalies = TelemetryService.detect_anomalies(
                device_id=device_id,
                period=params.get("period", "24h"),
                std_threshold=params.get("std_threshold", 3.0),
            )

            return Response(
                {
                    "device_id": device_id,
                    "count": len(anomalies),
                    "anomalies": anomalies,
                }
            )

        except Exception as e:
            logger.error(f"Error detecting anomalies: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"])
    def latest(self, request):
        """
        Get latest values for multiple devices.

        Query parameters:
        - device_ids: comma-separated device IDs
        - area: filter by area
        """
        device_ids_param = request.query_params.get("device_ids")
        device_ids = device_ids_param.split(",") if device_ids_param else None
        area = request.query_params.get("area")

        try:
            data = TelemetryService.get_latest_values(device_ids=device_ids, area=area)

            return Response({"count": len(data), "data": data})

        except Exception as e:
            logger.error(f"Error querying latest values: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def record(self, request):
        """
        Record telemetry data points.

        Request body:
        {
            "records": [
                {
                    "device_id": "temp-sensor-001",
                    "value": 1547.3,
                    "quality": "good",
                    "plant": "steel-plant-kigali",
                    "area": "melt-shop",
                    ...
                }
            ]
        }
        """
        serializer = BatchTelemetrySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            records = serializer.validated_data["records"]
            count = TelemetryService.record_telemetry(records)

            return Response(
                {
                    "recorded": count,
                    "message": f"Successfully recorded {count} telemetry points",
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            logger.error(f"Error recording telemetry: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["post"])
    def compare(self, request):
        """
        Compare multiple devices over a time range.

        Request body:
        {
            "device_ids": ["temp-sensor-001", "temp-sensor-002"],
            "start_time": "2024-03-20T00:00:00Z",
            "end_time": "2024-03-21T00:00:00Z",
            "interval": "1h"
        }
        """
        serializer = DeviceCompareSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        params = serializer.validated_data

        try:
            data = TelemetryService.compare_devices(
                device_ids=params["device_ids"],
                start_time=params["start_time"],
                end_time=params["end_time"],
                interval=params.get("interval", "1h"),
            )

            return Response({"device_count": len(params["device_ids"]), "data": data})

        except Exception as e:
            logger.error(f"Error comparing devices: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AreaViewSet(viewsets.ViewSet):
    """
    ViewSet for area-level telemetry operations.
    """

    @action(detail=False, methods=["get"], url_path="(?P<area>[^/.]+)/overview")
    def overview(self, request, area=None):
        """Get overview of all devices in an area."""
        try:
            data = TelemetryService.get_area_overview(area)
            serializer = AreaOverviewSerializer(data)
            return Response(serializer.data)

        except Exception as e:
            logger.error(f"Error querying area overview: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=False, methods=["get"], url_path="(?P<area>[^/.]+)/latest")
    def latest(self, request, area=None):
        """Get latest values for all devices in an area."""
        try:
            data = TelemetryService.get_latest_values(area=area)
            return Response({"area": area, "count": len(data), "data": data})

        except Exception as e:
            logger.error(f"Error querying area latest values: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class PlantDashboardView(APIView):
    """
    Plant-wide dashboard endpoint.
    """

    def get(self, request):
        """Get plant-wide dashboard data."""
        try:
            data = TelemetryService.get_plant_dashboard()
            return Response(data)

        except Exception as e:
            logger.error(f"Error querying plant dashboard: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TelemetryEventView(APIView):
    """
    Endpoint for recording telemetry events.
    """

    def post(self, request):
        """Record a telemetry event."""
        serializer = TelemetryEventSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            success = TelemetryService.record_event(
                device_id=data["device_id"],
                plant=data["plant"],
                area=data["area"],
                event_type=data["event_type"],
                severity=data["severity"],
                message=data["message"],
                value=data.get("value"),
                threshold=data.get("threshold"),
            )

            if success:
                return Response(
                    {"message": "Event recorded"}, status=status.HTTP_201_CREATED
                )
            else:
                return Response(
                    {"error": "Failed to record event"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(f"Error recording event: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TDengineSchemaView(APIView):
    """
    Endpoint for TDengine schema management.
    """

    def post(self, request):
        """Initialize TDengine schema."""
        try:
            success = init_tdengine_schema()

            if success:
                return Response({"message": "TDengine schema initialized"})
            else:
                return Response(
                    {"error": "Failed to initialize schema"},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

        except Exception as e:
            logger.error(f"Error initializing TDengine schema: {e}")
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
