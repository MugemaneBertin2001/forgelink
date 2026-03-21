"""URL configuration for steel plant simulator."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    DeviceProfileViewSet,
    SimulatedDeviceViewSet,
    SimulatedPLCViewSet,
    SimulationEventViewSet,
    SimulationSessionViewSet,
    SimulatorDashboardViewSet,
)

app_name = "simulator"

router = DefaultRouter()
router.register(r"profiles", DeviceProfileViewSet, basename="profile")
router.register(r"plcs", SimulatedPLCViewSet, basename="plc")
router.register(r"devices", SimulatedDeviceViewSet, basename="device")
router.register(r"sessions", SimulationSessionViewSet, basename="session")
router.register(r"events", SimulationEventViewSet, basename="event")
router.register(r"dashboard", SimulatorDashboardViewSet, basename="dashboard")

urlpatterns = [
    path("", include(router.urls)),
]
