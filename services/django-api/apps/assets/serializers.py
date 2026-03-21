"""REST API serializers for steel plant assets."""
from rest_framework import serializers
from .models import (
    Plant, Area, Line, Cell, DeviceType, Device, MaintenanceRecord
)


# ============================================
# Device Type Serializers
# ============================================

class DeviceTypeSerializer(serializers.ModelSerializer):
    """Serializer for device types."""
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = DeviceType
        fields = [
            'id', 'code', 'name', 'description',
            'default_unit', 'typical_min', 'typical_max',
            'icon', 'device_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_device_count(self, obj):
        return obj.devices.count()


class DeviceTypeMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for device types (nested use)."""

    class Meta:
        model = DeviceType
        fields = ['id', 'code', 'name', 'default_unit', 'icon']


# ============================================
# Device Serializers
# ============================================

class DeviceSerializer(serializers.ModelSerializer):
    """Full serializer for devices."""
    device_type = DeviceTypeMinimalSerializer(read_only=True)
    device_type_id = serializers.PrimaryKeyRelatedField(
        queryset=DeviceType.objects.all(),
        source='device_type',
        write_only=True
    )
    full_path = serializers.ReadOnlyField()
    uns_topic = serializers.ReadOnlyField()
    effective_unit = serializers.ReadOnlyField()
    cell_code = serializers.CharField(source='cell.code', read_only=True)
    line_code = serializers.CharField(source='cell.line.code', read_only=True)
    area_code = serializers.CharField(source='cell.line.area.code', read_only=True)
    plant_code = serializers.CharField(source='cell.line.area.plant.code', read_only=True)

    class Meta:
        model = Device
        fields = [
            'id', 'device_id', 'name', 'description',
            'cell', 'cell_code', 'line_code', 'area_code', 'plant_code',
            'device_type', 'device_type_id',
            'manufacturer', 'model', 'serial_number',
            'unit', 'precision', 'sampling_rate_ms', 'effective_unit',
            'warning_low', 'warning_high', 'critical_low', 'critical_high',
            'status', 'is_active', 'last_seen',
            'installed_at', 'last_calibration', 'next_calibration',
            'location_notes', 'tags',
            'full_path', 'uns_topic',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'last_seen', 'full_path', 'uns_topic',
            'created_at', 'updated_at'
        ]


class DeviceMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for devices (list views, nested use)."""
    device_type_code = serializers.CharField(source='device_type.code', read_only=True)
    area_code = serializers.CharField(source='cell.line.area.code', read_only=True)

    class Meta:
        model = Device
        fields = [
            'id', 'device_id', 'name', 'device_type_code',
            'area_code', 'status', 'is_active', 'last_seen'
        ]


class DeviceCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating devices."""

    class Meta:
        model = Device
        fields = [
            'device_id', 'name', 'description', 'cell', 'device_type',
            'manufacturer', 'model', 'serial_number',
            'unit', 'precision', 'sampling_rate_ms',
            'warning_low', 'warning_high', 'critical_low', 'critical_high',
            'installed_at', 'location_notes', 'tags'
        ]


class DeviceStatusSerializer(serializers.Serializer):
    """Serializer for device status updates."""
    status = serializers.ChoiceField(choices=Device.STATUS_CHOICES)


class DeviceThresholdsSerializer(serializers.Serializer):
    """Serializer for updating device thresholds."""
    warning_low = serializers.FloatField(required=False, allow_null=True)
    warning_high = serializers.FloatField(required=False, allow_null=True)
    critical_low = serializers.FloatField(required=False, allow_null=True)
    critical_high = serializers.FloatField(required=False, allow_null=True)


# ============================================
# Cell Serializers
# ============================================

class CellSerializer(serializers.ModelSerializer):
    """Full serializer for cells."""
    devices = DeviceMinimalSerializer(many=True, read_only=True)
    device_count = serializers.SerializerMethodField()
    line_code = serializers.CharField(source='line.code', read_only=True)
    area_code = serializers.CharField(source='line.area.code', read_only=True)

    class Meta:
        model = Cell
        fields = [
            'id', 'line', 'line_code', 'area_code',
            'code', 'name', 'description', 'is_active',
            'devices', 'device_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_device_count(self, obj):
        return obj.devices.count()


class CellMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for cells."""

    class Meta:
        model = Cell
        fields = ['id', 'code', 'name', 'is_active']


# ============================================
# Line Serializers
# ============================================

class LineSerializer(serializers.ModelSerializer):
    """Full serializer for lines."""
    cells = CellMinimalSerializer(many=True, read_only=True)
    cell_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()
    area_code = serializers.CharField(source='area.code', read_only=True)

    class Meta:
        model = Line
        fields = [
            'id', 'area', 'area_code',
            'code', 'name', 'description',
            'design_capacity', 'capacity_unit', 'is_active',
            'cells', 'cell_count', 'device_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_cell_count(self, obj):
        return obj.cells.count()

    def get_device_count(self, obj):
        return Device.objects.filter(cell__line=obj).count()


class LineMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for lines."""

    class Meta:
        model = Line
        fields = ['id', 'code', 'name', 'is_active']


# ============================================
# Area Serializers
# ============================================

class AreaSerializer(serializers.ModelSerializer):
    """Full serializer for areas."""
    lines = LineMinimalSerializer(many=True, read_only=True)
    line_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()
    plant_code = serializers.CharField(source='plant.code', read_only=True)

    class Meta:
        model = Area
        fields = [
            'id', 'plant', 'plant_code',
            'code', 'name', 'description',
            'area_type', 'sequence', 'is_active',
            'lines', 'line_count', 'device_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_line_count(self, obj):
        return obj.lines.count()

    def get_device_count(self, obj):
        return Device.objects.filter(cell__line__area=obj).count()


class AreaMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for areas."""

    class Meta:
        model = Area
        fields = ['id', 'code', 'name', 'area_type', 'is_active']


# ============================================
# Plant Serializers
# ============================================

class PlantSerializer(serializers.ModelSerializer):
    """Full serializer for plants."""
    areas = AreaMinimalSerializer(many=True, read_only=True)
    area_count = serializers.SerializerMethodField()
    device_count = serializers.SerializerMethodField()

    class Meta:
        model = Plant
        fields = [
            'id', 'code', 'name', 'description',
            'timezone', 'latitude', 'longitude', 'address',
            'is_active', 'commissioned_at',
            'areas', 'area_count', 'device_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_area_count(self, obj):
        return obj.areas.count()

    def get_device_count(self, obj):
        return Device.objects.filter(cell__line__area__plant=obj).count()


class PlantMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for plants."""

    class Meta:
        model = Plant
        fields = ['id', 'code', 'name', 'timezone', 'is_active']


# ============================================
# Maintenance Record Serializers
# ============================================

class MaintenanceRecordSerializer(serializers.ModelSerializer):
    """Full serializer for maintenance records."""
    device_id = serializers.CharField(source='device.device_id', read_only=True)

    class Meta:
        model = MaintenanceRecord
        fields = [
            'id', 'device', 'device_id',
            'maintenance_type', 'description',
            'performed_by', 'performed_at', 'duration_minutes',
            'parts_used', 'cost', 'next_scheduled',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MaintenanceRecordCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating maintenance records."""

    class Meta:
        model = MaintenanceRecord
        fields = [
            'device', 'maintenance_type', 'description',
            'performed_by', 'performed_at', 'duration_minutes',
            'parts_used', 'cost', 'next_scheduled'
        ]


# ============================================
# Hierarchy Serializers
# ============================================

class HierarchySerializer(serializers.Serializer):
    """Serializer for complete asset hierarchy."""
    plant = PlantSerializer()
    total_areas = serializers.IntegerField()
    total_lines = serializers.IntegerField()
    total_cells = serializers.IntegerField()
    total_devices = serializers.IntegerField()
    devices_online = serializers.IntegerField()
    devices_offline = serializers.IntegerField()
    devices_fault = serializers.IntegerField()


class DeviceSearchSerializer(serializers.Serializer):
    """Serializer for device search parameters."""
    query = serializers.CharField(required=False, allow_blank=True)
    area = serializers.CharField(required=False, allow_blank=True)
    device_type = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=['online', 'offline', 'maintenance', 'fault', 'calibrating'],
        required=False
    )
    is_active = serializers.BooleanField(required=False)
    tags = serializers.ListField(
        child=serializers.CharField(),
        required=False
    )
