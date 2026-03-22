"""Audit URL configuration."""

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from .views import AuditLogViewSet, AuditSummaryViewSet

router = DefaultRouter()
router.register(r"logs", AuditLogViewSet, basename="audit-logs")
router.register(r"summaries", AuditSummaryViewSet, basename="audit-summaries")

urlpatterns = [
    path("", include(router.urls)),
]
