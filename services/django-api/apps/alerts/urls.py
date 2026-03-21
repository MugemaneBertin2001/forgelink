"""URL configuration for alerts."""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import AlertHistoryViewSet, AlertRuleViewSet, AlertStatsView, AlertViewSet

app_name = "alerts"

router = DefaultRouter()
router.register(r"rules", AlertRuleViewSet, basename="rule")
router.register(r"alerts", AlertViewSet, basename="alert")
router.register(r"history", AlertHistoryViewSet, basename="history")

urlpatterns = [
    path("", include(router.urls)),
    path("stats/", AlertStatsView.as_view(), name="stats"),
]
