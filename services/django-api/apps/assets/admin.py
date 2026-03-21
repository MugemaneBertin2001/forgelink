"""Django Unfold admin for steel plant assets."""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Count
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from .models import (
    Plant, Area, Line, Cell, DeviceType, Device, MaintenanceRecord
)


# ============================================
# Inlines
# ============================================

class AreaInline(TabularInline):
    model = Area
    extra = 0
    fields = ['code', 'name', 'area_type', 'sequence', 'is_active']
    readonly_fields = []
    show_change_link = True


class LineInline(TabularInline):
    model = Line
    extra = 0
    fields = ['code', 'name', 'design_capacity', 'capacity_unit', 'is_active']
    show_change_link = True


class CellInline(TabularInline):
    model = Cell
    extra = 0
    fields = ['code', 'name', 'is_active']
    show_change_link = True


class DeviceInline(TabularInline):
    model = Device
    extra = 0
    fields = ['device_id', 'name', 'device_type', 'status', 'is_active']
    readonly_fields = ['status']
    show_change_link = True


class MaintenanceInline(TabularInline):
    model = MaintenanceRecord
    extra = 0
    fields = ['maintenance_type', 'description', 'performed_by', 'performed_at']
    readonly_fields = ['performed_at']
    max_num = 5


# ============================================
# Plant Admin
# ============================================

@admin.register(Plant)
class PlantAdmin(ModelAdmin):
    list_display = [
        'code', 'name', 'timezone_display', 'is_active_badge',
        'area_count', 'device_count', 'commissioned_at'
    ]
    list_filter = ['is_active', 'timezone']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [AreaInline]

    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'description')
        }),
        ('Location', {
            'fields': ('timezone', 'latitude', 'longitude', 'address')
        }),
        ('Status', {
            'fields': ('is_active', 'commissioned_at')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @display(description="Timezone", ordering="timezone")
    def timezone_display(self, obj):
        return obj.timezone

    @display(description="Active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Areas")
    def area_count(self, obj):
        return obj.areas.count()

    @display(description="Devices")
    def device_count(self, obj):
        return Device.objects.filter(
            cell__line__area__plant=obj
        ).count()


# ============================================
# Area Admin
# ============================================

@admin.register(Area)
class AreaAdmin(ModelAdmin):
    list_display = [
        'code', 'name', 'plant', 'area_type_badge', 'sequence',
        'is_active_badge', 'line_count', 'device_count'
    ]
    list_filter = ['plant', 'area_type', 'is_active']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [LineInline]

    fieldsets = (
        (None, {
            'fields': ('plant', 'code', 'name', 'description')
        }),
        ('Configuration', {
            'fields': ('area_type', 'sequence')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @display(description="Type")
    def area_type_badge(self, obj):
        colors = {
            'primary': '#2563eb',
            'secondary': '#7c3aed',
            'finishing': '#059669',
            'utility': '#6b7280',
            'storage': '#d97706',
            'quality': '#dc2626',
        }
        color = colors.get(obj.area_type, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_area_type_display()
        )

    @display(description="Active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Lines")
    def line_count(self, obj):
        return obj.lines.count()

    @display(description="Devices")
    def device_count(self, obj):
        return Device.objects.filter(cell__line__area=obj).count()


# ============================================
# Line Admin
# ============================================

@admin.register(Line)
class LineAdmin(ModelAdmin):
    list_display = [
        'code', 'name', 'area', 'capacity_display',
        'is_active_badge', 'cell_count', 'device_count'
    ]
    list_filter = ['area__plant', 'area', 'is_active']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [CellInline]

    fieldsets = (
        (None, {
            'fields': ('area', 'code', 'name', 'description')
        }),
        ('Capacity', {
            'fields': ('design_capacity', 'capacity_unit')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @display(description="Capacity")
    def capacity_display(self, obj):
        if obj.design_capacity:
            return f"{obj.design_capacity} {obj.capacity_unit}"
        return "-"

    @display(description="Active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Cells")
    def cell_count(self, obj):
        return obj.cells.count()

    @display(description="Devices")
    def device_count(self, obj):
        return Device.objects.filter(cell__line=obj).count()


# ============================================
# Cell Admin
# ============================================

@admin.register(Cell)
class CellAdmin(ModelAdmin):
    list_display = [
        'code', 'name', 'line', 'is_active_badge', 'device_count'
    ]
    list_filter = ['line__area__plant', 'line__area', 'line', 'is_active']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    inlines = [DeviceInline]

    fieldsets = (
        (None, {
            'fields': ('line', 'code', 'name', 'description')
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @display(description="Active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Devices")
    def device_count(self, obj):
        return obj.devices.count()


# ============================================
# Device Type Admin
# ============================================

@admin.register(DeviceType)
class DeviceTypeAdmin(ModelAdmin):
    list_display = [
        'code', 'name', 'default_unit', 'typical_range', 'device_count'
    ]
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']

    fieldsets = (
        (None, {
            'fields': ('code', 'name', 'description', 'icon')
        }),
        ('Measurement', {
            'fields': ('default_unit', 'typical_min', 'typical_max')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @display(description="Typical Range")
    def typical_range(self, obj):
        if obj.typical_min is not None and obj.typical_max is not None:
            return f"{obj.typical_min} - {obj.typical_max} {obj.default_unit}"
        return "-"

    @display(description="Devices")
    def device_count(self, obj):
        return obj.devices.count()


# ============================================
# Device Admin
# ============================================

@admin.register(Device)
class DeviceAdmin(ModelAdmin):
    list_display = [
        'device_id', 'name', 'device_type', 'cell',
        'status_badge', 'is_active_badge', 'last_seen', 'thresholds_display'
    ]
    list_filter = [
        'status', 'is_active', 'device_type',
        'cell__line__area__plant', 'cell__line__area', 'cell__line'
    ]
    search_fields = ['device_id', 'name', 'description', 'serial_number']
    readonly_fields = ['id', 'last_seen', 'created_at', 'updated_at', 'full_path', 'uns_topic']
    inlines = [MaintenanceInline]
    list_per_page = 50

    fieldsets = (
        (None, {
            'fields': ('device_id', 'name', 'description', 'cell', 'device_type')
        }),
        ('Device Details', {
            'fields': ('manufacturer', 'model', 'serial_number')
        }),
        ('Measurement', {
            'fields': ('unit', 'precision', 'sampling_rate_ms')
        }),
        ('Thresholds', {
            'fields': (
                ('warning_low', 'warning_high'),
                ('critical_low', 'critical_high')
            )
        }),
        ('Status', {
            'fields': ('status', 'is_active', 'last_seen')
        }),
        ('Installation', {
            'fields': ('installed_at', 'last_calibration', 'next_calibration', 'location_notes')
        }),
        ('Tags', {
            'fields': ('tags',)
        }),
        ('Paths', {
            'fields': ('full_path', 'uns_topic'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    actions = ['mark_online', 'mark_offline', 'mark_maintenance', 'activate', 'deactivate']

    @display(description="Status")
    def status_badge(self, obj):
        colors = {
            'online': '#059669',
            'offline': '#6b7280',
            'maintenance': '#d97706',
            'fault': '#dc2626',
            'calibrating': '#2563eb',
        }
        color = colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px; text-transform: uppercase;">{}</span>',
            color, obj.status
        )

    @display(description="Active", boolean=True)
    def is_active_badge(self, obj):
        return obj.is_active

    @display(description="Thresholds")
    def thresholds_display(self, obj):
        parts = []
        if obj.critical_low is not None:
            parts.append(f"CL:{obj.critical_low}")
        if obj.warning_low is not None:
            parts.append(f"WL:{obj.warning_low}")
        if obj.warning_high is not None:
            parts.append(f"WH:{obj.warning_high}")
        if obj.critical_high is not None:
            parts.append(f"CH:{obj.critical_high}")
        return " | ".join(parts) if parts else "-"

    @admin.action(description="Mark selected devices as Online")
    def mark_online(self, request, queryset):
        count = queryset.update(status='online')
        self.message_user(request, f"{count} devices marked as online.")

    @admin.action(description="Mark selected devices as Offline")
    def mark_offline(self, request, queryset):
        count = queryset.update(status='offline')
        self.message_user(request, f"{count} devices marked as offline.")

    @admin.action(description="Mark selected devices as Maintenance")
    def mark_maintenance(self, request, queryset):
        count = queryset.update(status='maintenance')
        self.message_user(request, f"{count} devices marked as maintenance.")

    @admin.action(description="Activate selected devices")
    def activate(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} devices activated.")

    @admin.action(description="Deactivate selected devices")
    def deactivate(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} devices deactivated.")


# ============================================
# Maintenance Record Admin
# ============================================

@admin.register(MaintenanceRecord)
class MaintenanceRecordAdmin(ModelAdmin):
    list_display = [
        'device', 'maintenance_type_badge', 'performed_by',
        'performed_at', 'duration_display', 'cost_display', 'next_scheduled'
    ]
    list_filter = ['maintenance_type', 'device__device_type', 'performed_at']
    search_fields = ['device__device_id', 'description', 'performed_by']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'performed_at'

    fieldsets = (
        (None, {
            'fields': ('device', 'maintenance_type')
        }),
        ('Details', {
            'fields': ('description', 'performed_by', 'performed_at', 'duration_minutes')
        }),
        ('Parts & Cost', {
            'fields': ('parts_used', 'cost')
        }),
        ('Scheduling', {
            'fields': ('next_scheduled',)
        }),
        ('Metadata', {
            'fields': ('id', 'created_at'),
            'classes': ('collapse',)
        }),
    )

    @display(description="Type")
    def maintenance_type_badge(self, obj):
        colors = {
            'preventive': '#059669',
            'corrective': '#dc2626',
            'calibration': '#2563eb',
            'inspection': '#6b7280',
            'replacement': '#d97706',
        }
        color = colors.get(obj.maintenance_type, '#6b7280')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 2px 8px; '
            'border-radius: 4px; font-size: 11px;">{}</span>',
            color, obj.get_maintenance_type_display()
        )

    @display(description="Duration")
    def duration_display(self, obj):
        if obj.duration_minutes:
            hours = obj.duration_minutes // 60
            minutes = obj.duration_minutes % 60
            if hours > 0:
                return f"{hours}h {minutes}m"
            return f"{minutes}m"
        return "-"

    @display(description="Cost")
    def cost_display(self, obj):
        if obj.cost:
            return f"${obj.cost:,.2f}"
        return "-"
