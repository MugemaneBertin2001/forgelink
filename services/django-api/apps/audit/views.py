"""Audit views for REST API."""

from datetime import date, timedelta

from django.db.models import Avg, Count
from django.utils import timezone

from django_filters import rest_framework as filters
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import HasPermission

from .models import AuditLog, AuditSummary
from .serializers import (
    AuditLogListSerializer,
    AuditLogSerializer,
    AuditStatsSerializer,
    AuditSummarySerializer,
)


class AuditLogFilter(filters.FilterSet):
    """Filter for audit logs."""

    user_id = filters.CharFilter(lookup_expr="icontains")
    action = filters.ChoiceFilter(choices=AuditLog.ActionType.choices)
    resource_type = filters.CharFilter(lookup_expr="iexact")
    status_code = filters.NumberFilter()
    status_code_gte = filters.NumberFilter(field_name="status_code", lookup_expr="gte")
    status_code_lte = filters.NumberFilter(field_name="status_code", lookup_expr="lte")
    timestamp_after = filters.DateTimeFilter(field_name="timestamp", lookup_expr="gte")
    timestamp_before = filters.DateTimeFilter(field_name="timestamp", lookup_expr="lte")
    date = filters.DateFilter(field_name="timestamp", lookup_expr="date")
    ip_address = filters.CharFilter(lookup_expr="icontains")

    class Meta:
        model = AuditLog
        fields = [
            "user_id",
            "action",
            "resource_type",
            "status_code",
            "ip_address",
        ]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for audit logs (read-only)."""

    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    filterset_class = AuditLogFilter
    permission_classes = [HasPermission("admin.view_audit")]
    ordering = ["-timestamp"]
    ordering_fields = ["timestamp", "user_id", "action", "status_code", "duration_ms"]

    def get_serializer_class(self):
        if self.action == "list":
            return AuditLogListSerializer
        return AuditLogSerializer

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """Get audit statistics."""
        today = timezone.now().date()
        logs_today = AuditLog.objects.filter(timestamp__date=today)

        stats = {
            "total_logs": AuditLog.objects.count(),
            "logs_today": logs_today.count(),
            "unique_users_today": logs_today.exclude(user_id__isnull=True)
            .values("user_id")
            .distinct()
            .count(),
            "failed_requests_today": logs_today.filter(status_code__gte=400).count(),
            "avg_response_time_today": logs_today.exclude(
                duration_ms__isnull=True
            ).aggregate(avg=Avg("duration_ms"))["avg"],
            "actions_by_type": dict(
                logs_today.values("action")
                .annotate(count=Count("id"))
                .values_list("action", "count")
            ),
            "top_users": list(
                logs_today.exclude(user_id__isnull=True)
                .values("user_id")
                .annotate(count=Count("id"))
                .order_by("-count")[:5]
            ),
            "recent_errors": list(
                logs_today.filter(status_code__gte=400)
                .values("resource", "status_code", "timestamp", "user_id")
                .order_by("-timestamp")[:10]
            ),
        }

        serializer = AuditStatsSerializer(stats)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_user(self, request):
        """Get audit logs for a specific user."""
        user_id = request.query_params.get("user_id")
        if not user_id:
            return Response(
                {"error": "user_id parameter required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        logs = self.get_queryset().filter(user_id__icontains=user_id)[:100]
        serializer = AuditLogListSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def by_resource(self, request):
        """Get audit logs for a specific resource."""
        resource_type = request.query_params.get("resource_type")
        resource_id = request.query_params.get("resource_id")

        queryset = self.get_queryset()
        if resource_type:
            queryset = queryset.filter(resource_type=resource_type)
        if resource_id:
            queryset = queryset.filter(resource_id=resource_id)

        logs = queryset[:100]
        serializer = AuditLogListSerializer(logs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def errors(self, request):
        """Get recent error logs (4xx and 5xx responses)."""
        days = int(request.query_params.get("days", 7))
        since = timezone.now() - timedelta(days=days)

        logs = (
            self.get_queryset()
            .filter(timestamp__gte=since, status_code__gte=400)
            .order_by("-timestamp")[:100]
        )
        serializer = AuditLogListSerializer(logs, many=True)
        return Response(serializer.data)


class AuditSummaryFilter(filters.FilterSet):
    """Filter for audit summaries."""

    date_after = filters.DateFilter(field_name="date", lookup_expr="gte")
    date_before = filters.DateFilter(field_name="date", lookup_expr="lte")

    class Meta:
        model = AuditSummary
        fields = ["date"]


class AuditSummaryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for audit summaries (read-only)."""

    queryset = AuditSummary.objects.all()
    serializer_class = AuditSummarySerializer
    filterset_class = AuditSummaryFilter
    permission_classes = [HasPermission("admin.view_audit")]
    ordering = ["-date"]

    @action(detail=False, methods=["post"])
    def generate(self, request):
        """Generate summary for a specific date or yesterday."""
        target_date = request.data.get("date")
        if target_date:
            try:
                target_date = date.fromisoformat(target_date)
            except ValueError:
                return Response(
                    {"error": "Invalid date format. Use YYYY-MM-DD"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_date = timezone.now().date() - timedelta(days=1)

        summary = AuditSummary.generate_for_date(target_date)
        serializer = AuditSummarySerializer(summary)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def dashboard(self, request):
        """Get dashboard data with recent summaries and trends."""
        days = int(request.query_params.get("days", 7))
        since = timezone.now().date() - timedelta(days=days)

        summaries = self.get_queryset().filter(date__gte=since).order_by("date")

        return Response(
            {
                "summaries": AuditSummarySerializer(summaries, many=True).data,
                "total_requests": sum(s.total_requests for s in summaries),
                "total_errors": sum(s.failed_requests for s in summaries),
                "avg_daily_users": (
                    sum(s.unique_users for s in summaries) / len(summaries)
                    if summaries
                    else 0
                ),
            }
        )
