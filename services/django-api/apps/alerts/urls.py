"""URL configuration for alerts."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AlertRuleViewSet,
    AlertViewSet,
    AlertHistoryViewSet,
    AlertStatsView,
)

app_name = 'alerts'

router = DefaultRouter()
router.register(r'rules', AlertRuleViewSet, basename='rule')
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'history', AlertHistoryViewSet, basename='history')

urlpatterns = [
    path('', include(router.urls)),
    path('stats/', AlertStatsView.as_view(), name='stats'),
]
