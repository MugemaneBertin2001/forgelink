"""URL configuration for telemetry REST API."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    AreaViewSet,
    PlantDashboardView,
    TDengineSchemaView,
    TelemetryEventView,
    TelemetryViewSet,
)

app_name = "telemetry"

router = DefaultRouter()
router.register(r"data", TelemetryViewSet, basename="telemetry")
router.register(r"areas", AreaViewSet, basename="area")

urlpatterns = [
    # Router URLs
    path("", include(router.urls)),
    # Additional endpoints
    path("dashboard/", PlantDashboardView.as_view(), name="plant-dashboard"),
    path("events/", TelemetryEventView.as_view(), name="telemetry-event"),
    path("schema/init/", TDengineSchemaView.as_view(), name="tdengine-schema"),
]
