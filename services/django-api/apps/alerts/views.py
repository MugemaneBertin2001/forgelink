"""REST API views for alerts."""

import logging

from rest_framework import filters, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from django_filters.rest_framework import DjangoFilterBackend

from apps.core.permissions import (
    AreaAccessPermission,
    CanAcknowledgeAlerts,
    CanManageAlertRules,
    CanResolveAlerts,
    CanViewAlerts,
)

from .models import Alert, AlertHistory, AlertRule
from .serializers import (
    AlertAcknowledgeSerializer,
    AlertHistorySerializer,
    AlertResolveSerializer,
    AlertRuleSerializer,
    AlertSerializer,
    AlertStatsSerializer,
)
from .services import AlertService

logger = logging.getLogger(__name__)


class AlertRuleViewSet(viewsets.ModelViewSet):
    """
    ViewSet for alert rule management.

    Permissions:
    - GET: alerts.view
    - POST: alerts.create_rule
    - PUT/PATCH: alerts.update_rule
    - DELETE: alerts.delete_rule
    """

    queryset = AlertRule.objects.select_related("device", "device_type").all()
    serializer_class = AlertRuleSerializer
    permission_classes = [CanManageAlertRules]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["severity", "rule_type", "is_active", "notify_slack"]
    search_fields = ["name", "description", "device__device_id", "area_code"]
    ordering_fields = ["severity", "name", "created_at"]
    ordering = ["-severity", "name"]

    @action(detail=True, methods=["post"])
    def activate(self, request, pk=None):
        """Activate an alert rule."""
        rule = self.get_object()
        rule.is_active = True
        rule.save(update_fields=["is_active", "updated_at"])
        return Response({"status": "activated"})

    @action(detail=True, methods=["post"])
    def deactivate(self, request, pk=None):
        """Deactivate an alert rule."""
        rule = self.get_object()
        rule.is_active = False
        rule.save(update_fields=["is_active", "updated_at"])
        return Response({"status": "deactivated"})


class AlertViewSet(viewsets.ModelViewSet):
    """
    ViewSet for alert management.

    Permissions:
    - GET: alerts.view
    - POST actions (acknowledge, resolve): alerts.acknowledge, alerts.resolve
    """

    queryset = Alert.objects.select_related("device", "rule").all()
    serializer_class = AlertSerializer
    permission_classes = [CanViewAlerts, AreaAccessPermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["severity", "status", "alert_type"]
    search_fields = ["device__device_id", "message"]
    ordering_fields = ["triggered_at", "severity"]
    ordering = ["-triggered_at"]
    http_method_names = ["get", "post", "head", "options"]  # No PUT/DELETE

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Get active alerts."""
        area = request.query_params.get("area")
        severity = request.query_params.get("severity")
        limit = int(request.query_params.get("limit", 100))

        alerts = AlertService.get_active_alerts(
            area=area, severity=severity, limit=limit
        )

        serializer = AlertSerializer(alerts, many=True)
        return Response({"count": len(alerts), "alerts": serializer.data})

    @action(detail=True, methods=["post"], permission_classes=[CanAcknowledgeAlerts])
    def acknowledge(self, request, pk=None):
        """Acknowledge an alert. Requires: alerts.acknowledge"""
        serializer = AlertAcknowledgeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use authenticated user's email if not provided
        user = serializer.validated_data.get("user") or request.user.email

        alert = AlertService.acknowledge_alert(str(pk), user)

        if alert:
            return Response(AlertSerializer(alert).data)
        else:
            return Response(
                {"error": "Alert not found or not active"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=True, methods=["post"], permission_classes=[CanResolveAlerts])
    def resolve(self, request, pk=None):
        """Resolve an alert. Requires: alerts.resolve"""
        serializer = AlertResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Use authenticated user's email if not provided
        user = serializer.validated_data.get("user") or request.user.email

        alert = AlertService.resolve_alert(
            str(pk), user, serializer.validated_data.get("notes", "")
        )

        if alert:
            return Response(AlertSerializer(alert).data)
        else:
            return Response(
                {"error": "Alert not found or already resolved"},
                status=status.HTTP_404_NOT_FOUND,
            )

    @action(detail=False, methods=["post"], permission_classes=[CanAcknowledgeAlerts])
    def acknowledge_bulk(self, request):
        """Acknowledge multiple alerts. Requires: alerts.acknowledge"""
        alert_ids = request.data.get("alert_ids", [])
        user = request.data.get("user") or request.user.email

        acknowledged = []
        for alert_id in alert_ids:
            alert = AlertService.acknowledge_alert(alert_id, user)
            if alert:
                acknowledged.append(str(alert.id))

        return Response({"acknowledged": len(acknowledged), "alert_ids": acknowledged})

    @action(detail=False, methods=["post"], permission_classes=[CanResolveAlerts])
    def resolve_bulk(self, request):
        """Resolve multiple alerts. Requires: alerts.resolve"""
        alert_ids = request.data.get("alert_ids", [])
        user = request.data.get("user") or request.user.email
        notes = request.data.get("notes", "")

        resolved = []
        for alert_id in alert_ids:
            alert = AlertService.resolve_alert(alert_id, user, notes)
            if alert:
                resolved.append(str(alert.id))

        return Response({"resolved": len(resolved), "alert_ids": resolved})


class AlertHistoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet for alert history (read-only).

    Permissions: alerts.view
    """

    queryset = AlertHistory.objects.all()
    serializer_class = AlertHistorySerializer
    permission_classes = [CanViewAlerts]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["severity", "area", "device_id"]
    search_fields = ["device_id", "message", "area"]
    ordering_fields = ["triggered_at", "duration_seconds", "severity"]
    ordering = ["-triggered_at"]


class AlertStatsView(APIView):
    """
    Alert statistics endpoint.

    Permissions: alerts.view
    """

    permission_classes = [CanViewAlerts]

    def get(self, request):
        """Get alert statistics."""
        hours = int(request.query_params.get("hours", 24))
        stats = AlertService.get_alert_stats(hours)
        serializer = AlertStatsSerializer(stats)
        return Response(serializer.data)
