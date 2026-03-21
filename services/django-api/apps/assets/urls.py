"""URL configuration for steel plant assets."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    PlantViewSet,
    AreaViewSet,
    LineViewSet,
    CellViewSet,
    DeviceTypeViewSet,
    DeviceViewSet,
    MaintenanceRecordViewSet,
    AssetDashboardView,
)

app_name = 'assets'

router = DefaultRouter()
router.register(r'plants', PlantViewSet, basename='plant')
router.register(r'areas', AreaViewSet, basename='area')
router.register(r'lines', LineViewSet, basename='line')
router.register(r'cells', CellViewSet, basename='cell')
router.register(r'device-types', DeviceTypeViewSet, basename='device-type')
router.register(r'devices', DeviceViewSet, basename='device')
router.register(r'maintenance', MaintenanceRecordViewSet, basename='maintenance')

urlpatterns = [
    # Router URLs
    path('', include(router.urls)),

    # Dashboard
    path('dashboard/', AssetDashboardView.as_view(), name='asset-dashboard'),
]
