"""
Asset models following ISA-95 equipment hierarchy.

Hierarchy:
    Plant → Area → Line → Cell → Device

Steel plant areas (from CLAUDE.md):
- Melt Shop (EAF, LRF, ladle cars)
- Continuous Casting (tundish, mold, strand guide)
- Rolling Mill (reheating furnace, stands)
- Finishing (straightening, inspection, bundling)
"""
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone


class Plant(models.Model):
    """
    Top-level facility in ISA-95 hierarchy.

    A plant is a complete manufacturing facility.
    ForgeLink: steel-plant-kigali
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique plant code (e.g., steel-plant-kigali)"
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    # Location
    timezone = models.CharField(max_length=64, default='Africa/Kigali')
    latitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=10, decimal_places=7, null=True, blank=True
    )
    address = models.TextField(blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    commissioned_at = models.DateField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assets_plant'
        ordering = ['name']
        verbose_name = 'Plant'
        verbose_name_plural = 'Plants'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Area(models.Model):
    """
    Production area within a plant.

    Examples: Melt Shop, Continuous Casting, Rolling Mill, Finishing
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plant = models.ForeignKey(
        Plant,
        on_delete=models.CASCADE,
        related_name='areas'
    )
    code = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Area code (e.g., melt-shop)"
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    # Area type for categorization
    AREA_TYPES = [
        ('primary', 'Primary Production'),
        ('secondary', 'Secondary Processing'),
        ('finishing', 'Finishing'),
        ('utility', 'Utilities'),
        ('storage', 'Storage'),
        ('quality', 'Quality Control'),
    ]
    area_type = models.CharField(
        max_length=20,
        choices=AREA_TYPES,
        default='primary'
    )

    # Production flow order
    sequence = models.IntegerField(
        default=0,
        help_text="Order in production flow (1=first, 2=second, etc.)"
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assets_area'
        ordering = ['plant', 'sequence', 'name']
        unique_together = [['plant', 'code']]
        verbose_name = 'Area'
        verbose_name_plural = 'Areas'

    def __str__(self):
        return f"{self.plant.code}/{self.code}"


class Line(models.Model):
    """
    Production line within an area.

    Examples: EAF-1, Caster-1, Stand-6
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    area = models.ForeignKey(
        Area,
        on_delete=models.CASCADE,
        related_name='lines'
    )
    code = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Line code (e.g., eaf-1)"
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    # Capacity
    design_capacity = models.FloatField(
        null=True, blank=True,
        help_text="Design capacity (tons/hour or units/hour)"
    )
    capacity_unit = models.CharField(
        max_length=32,
        blank=True,
        default='tons/hour'
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assets_line'
        ordering = ['area', 'code']
        unique_together = [['area', 'code']]
        verbose_name = 'Production Line'
        verbose_name_plural = 'Production Lines'

    def __str__(self):
        return f"{self.area}/{self.code}"


class Cell(models.Model):
    """
    Work cell within a production line.

    Examples: Electrode-A, Mold, Strand-Guide
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    line = models.ForeignKey(
        Line,
        on_delete=models.CASCADE,
        related_name='cells'
    )
    code = models.CharField(
        max_length=64,
        db_index=True,
        help_text="Cell code (e.g., electrode-a)"
    )
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assets_cell'
        ordering = ['line', 'code']
        unique_together = [['line', 'code']]
        verbose_name = 'Work Cell'
        verbose_name_plural = 'Work Cells'

    def __str__(self):
        return f"{self.line}/{self.code}"


class DeviceType(models.Model):
    """
    Type of measurement device or sensor.

    Examples: temperature, pressure, vibration, flow, level
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    code = models.CharField(
        max_length=32,
        unique=True,
        db_index=True,
        help_text="Type code (e.g., temperature)"
    )
    name = models.CharField(max_length=64)
    description = models.TextField(blank=True)

    # Measurement details
    default_unit = models.CharField(
        max_length=20,
        help_text="Default unit of measurement (e.g., °C, bar, mm/s)"
    )

    # Typical thresholds (can be overridden per device)
    typical_min = models.FloatField(
        null=True, blank=True,
        help_text="Typical minimum value"
    )
    typical_max = models.FloatField(
        null=True, blank=True,
        help_text="Typical maximum value"
    )

    # Icon for UI
    icon = models.CharField(max_length=32, blank=True, default='sensor')

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assets_device_type'
        ordering = ['name']
        verbose_name = 'Device Type'
        verbose_name_plural = 'Device Types'

    def __str__(self):
        return f"{self.name} ({self.code})"


class Device(models.Model):
    """
    Individual measurement device or sensor.

    This is the lowest level in the ISA-95 hierarchy.
    Each device maps to a telemetry source in TDengine.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        help_text="Unique device ID (e.g., temp-sensor-001)"
    )

    # Hierarchy
    cell = models.ForeignKey(
        Cell,
        on_delete=models.CASCADE,
        related_name='devices'
    )
    device_type = models.ForeignKey(
        DeviceType,
        on_delete=models.PROTECT,
        related_name='devices'
    )

    # Device details
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)
    manufacturer = models.CharField(max_length=128, blank=True)
    model = models.CharField(max_length=128, blank=True)
    serial_number = models.CharField(max_length=128, blank=True)

    # Measurement configuration
    unit = models.CharField(
        max_length=20,
        blank=True,
        help_text="Override unit (uses device type default if empty)"
    )
    precision = models.IntegerField(
        default=2,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Decimal places for display"
    )
    sampling_rate_ms = models.IntegerField(
        default=1000,
        validators=[MinValueValidator(100)],
        help_text="Expected sampling rate in milliseconds"
    )

    # Thresholds
    warning_low = models.FloatField(null=True, blank=True)
    warning_high = models.FloatField(null=True, blank=True)
    critical_low = models.FloatField(null=True, blank=True)
    critical_high = models.FloatField(null=True, blank=True)

    # Status
    STATUS_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('maintenance', 'Maintenance'),
        ('fault', 'Fault'),
        ('calibrating', 'Calibrating'),
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='offline'
    )
    is_active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)

    # Installation
    installed_at = models.DateField(null=True, blank=True)
    last_calibration = models.DateField(null=True, blank=True)
    next_calibration = models.DateField(null=True, blank=True)

    # Physical location
    location_notes = models.TextField(
        blank=True,
        help_text="Physical location description"
    )

    # Tags for filtering
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Tags for filtering (e.g., ['critical', 'eaf'])"
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'assets_device'
        ordering = ['device_id']
        verbose_name = 'Device'
        verbose_name_plural = 'Devices'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['device_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.device_id} ({self.name})"

    @property
    def full_path(self) -> str:
        """Get the full hierarchical path."""
        cell = self.cell
        line = cell.line
        area = line.area
        plant = area.plant
        return f"{plant.code}/{area.code}/{line.code}/{cell.code}/{self.device_id}"

    @property
    def uns_topic(self) -> str:
        """Get the UNS MQTT topic for this device."""
        cell = self.cell
        line = cell.line
        area = line.area
        plant = area.plant
        return f"forgelink/{plant.code}/{area.code}/{line.code}/{cell.code}/{self.device_id}/telemetry"

    @property
    def effective_unit(self) -> str:
        """Get the effective unit (device override or type default)."""
        return self.unit or self.device_type.default_unit

    def update_status(self, new_status: str):
        """Update device status and last_seen timestamp."""
        self.status = new_status
        if new_status == 'online':
            self.last_seen = timezone.now()
        self.save(update_fields=['status', 'last_seen', 'updated_at'])


class MaintenanceRecord(models.Model):
    """
    Maintenance history for devices.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        Device,
        on_delete=models.CASCADE,
        related_name='maintenance_records'
    )

    # Maintenance type
    MAINTENANCE_TYPES = [
        ('preventive', 'Preventive Maintenance'),
        ('corrective', 'Corrective Maintenance'),
        ('calibration', 'Calibration'),
        ('inspection', 'Inspection'),
        ('replacement', 'Replacement'),
    ]
    maintenance_type = models.CharField(
        max_length=20,
        choices=MAINTENANCE_TYPES
    )

    # Details
    description = models.TextField()
    performed_by = models.CharField(max_length=128)
    performed_at = models.DateTimeField()
    duration_minutes = models.IntegerField(null=True, blank=True)

    # Parts/costs
    parts_used = models.TextField(blank=True)
    cost = models.DecimalField(
        max_digits=10, decimal_places=2,
        null=True, blank=True
    )

    # Next scheduled
    next_scheduled = models.DateField(null=True, blank=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'assets_maintenance_record'
        ordering = ['-performed_at']
        verbose_name = 'Maintenance Record'
        verbose_name_plural = 'Maintenance Records'

    def __str__(self):
        return f"{self.device.device_id} - {self.maintenance_type} ({self.performed_at.date()})"
