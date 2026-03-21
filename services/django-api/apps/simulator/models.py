"""Simulator models for full OPC-UA stack simulation."""

import uuid
from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class DeviceProfile(models.Model):
    """
    Template for sensor types with realistic physics parameters.
    Defines behavior characteristics for different sensor types in steel manufacturing.
    """

    class SensorType(models.TextChoices):
        TEMPERATURE = "temperature", "Temperature Sensor"
        PRESSURE = "pressure", "Pressure Sensor"
        FLOW = "flow", "Flow Meter"
        LEVEL = "level", "Level Sensor"
        VIBRATION = "vibration", "Vibration Sensor"
        CURRENT = "current", "Current Sensor"
        VOLTAGE = "voltage", "Voltage Sensor"
        SPEED = "speed", "Speed Sensor"
        FORCE = "force", "Force Sensor"
        POSITION = "position", "Position Sensor"
        WEIGHT = "weight", "Weight Sensor"
        HUMIDITY = "humidity", "Humidity Sensor"
        GAS_CONCENTRATION = "gas", "Gas Concentration"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    sensor_type = models.CharField(max_length=20, choices=SensorType.choices)
    description = models.TextField(blank=True)

    # Value range
    min_value = models.DecimalField(max_digits=12, decimal_places=4)
    max_value = models.DecimalField(max_digits=12, decimal_places=4)
    unit = models.CharField(max_length=20)

    # Physics simulation parameters
    noise_factor = models.DecimalField(
        max_digits=5,
        decimal_places=4,
        default=0.01,
        validators=[MinValueValidator(0), MaxValueValidator(1)],
        help_text="Random noise as fraction of range (0.01 = 1%)",
    )
    drift_rate = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        default=0.0001,
        help_text="Value drift per second as fraction of range",
    )
    response_time_ms = models.PositiveIntegerField(
        default=100, help_text="Sensor response time in milliseconds"
    )
    dead_band = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=0.5,
        help_text="Minimum change to report (absolute value)",
    )

    # Threshold for events
    high_threshold = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    low_threshold = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    critical_high = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    critical_low = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )

    # Failure simulation
    mtbf_hours = models.PositiveIntegerField(
        default=8760, help_text="Mean Time Between Failures in hours"
    )
    mttr_minutes = models.PositiveIntegerField(
        default=30, help_text="Mean Time To Repair in minutes"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Device Profile"
        verbose_name_plural = "Device Profiles"
        ordering = ["sensor_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.sensor_type})"


class SimulatedPLC(models.Model):
    """
    Represents a simulated PLC (Programmable Logic Controller).
    Groups multiple devices and maps to OPC-UA server namespace.
    """

    class PLCType(models.TextChoices):
        SIEMENS_S7 = "siemens_s7", "Siemens S7-1500"
        ALLEN_BRADLEY = "allen_bradley", "Allen-Bradley ControlLogix"
        SCHNEIDER = "schneider", "Schneider Modicon"
        GENERIC = "generic", "Generic PLC"

    class Area(models.TextChoices):
        MELT_SHOP = "melt-shop", "Melt Shop"
        CONTINUOUS_CASTING = "continuous-casting", "Continuous Casting"
        ROLLING_MILL = "rolling-mill", "Rolling Mill"
        FINISHING = "finishing", "Finishing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    plc_type = models.CharField(
        max_length=20, choices=PLCType.choices, default=PLCType.GENERIC
    )

    # Location in ISA-95 hierarchy
    plant = models.CharField(max_length=64, default="steel-plant-kigali")
    area = models.CharField(max_length=32, choices=Area.choices)
    line = models.CharField(max_length=32, help_text="e.g., eaf-1, caster-1, roughing")
    cell = models.CharField(
        max_length=32, blank=True, help_text="e.g., electrode-a, mold"
    )

    # OPC-UA configuration
    opc_namespace = models.CharField(
        max_length=100, blank=True, help_text="OPC-UA namespace URI"
    )
    opc_node_id_prefix = models.CharField(
        max_length=200, blank=True, help_text="Prefix for OPC-UA node IDs"
    )

    # Status
    is_online = models.BooleanField(default=False)
    is_simulating = models.BooleanField(default=False)
    last_heartbeat = models.DateTimeField(null=True, blank=True)

    # Communication settings
    scan_rate_ms = models.PositiveIntegerField(
        default=1000, help_text="How often to publish values (milliseconds)"
    )
    publish_rate_ms = models.PositiveIntegerField(
        default=1000, help_text="MQTT publish interval (milliseconds)"
    )

    # Metadata
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    firmware_version = models.CharField(max_length=20, blank=True)
    description = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Simulated PLC"
        verbose_name_plural = "Simulated PLCs"
        ordering = ["area", "line", "name"]
        unique_together = ["plant", "area", "line", "cell", "name"]

    def __str__(self):
        return f"{self.name} ({self.area}/{self.line})"

    @property
    def topic_prefix(self) -> str:
        """Generate MQTT topic prefix for this PLC's location."""
        parts = ["forgelink", self.plant, self.area, self.line]
        if self.cell:
            parts.append(self.cell)
        return "/".join(parts)

    @property
    def opc_path(self) -> str:
        """Generate OPC-UA path for this PLC."""
        parts = [
            self.plant.replace("-", ""),
            self.area.replace("-", ""),
            self.line.replace("-", ""),
        ]
        if self.cell:
            parts.append(self.cell.replace("-", ""))
        return "/".join(parts)


class SimulatedDevice(models.Model):
    """
    Individual simulated sensor/actuator connected to a PLC.
    Each device has its own OPC-UA node and publishes to a unique MQTT topic.
    """

    class Status(models.TextChoices):
        OFFLINE = "offline", "Offline"
        ONLINE = "online", "Online"
        RUNNING = "running", "Running (Simulating)"
        FAULT = "fault", "Fault"
        MAINTENANCE = "maintenance", "Under Maintenance"

    class Quality(models.TextChoices):
        GOOD = "good", "Good"
        BAD = "bad", "Bad"
        UNCERTAIN = "uncertain", "Uncertain"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device_id = models.CharField(
        max_length=64, help_text="Unique device identifier (e.g., temp-sensor-001)"
    )
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Relationships
    plc = models.ForeignKey(
        SimulatedPLC, on_delete=models.CASCADE, related_name="devices"
    )
    profile = models.ForeignKey(
        DeviceProfile, on_delete=models.PROTECT, related_name="devices"
    )

    # Current state
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OFFLINE
    )
    current_value = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    target_value = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Target value for simulation (sensor will trend toward this)",
    )
    quality = models.CharField(
        max_length=20, choices=Quality.choices, default=Quality.GOOD
    )
    sequence_number = models.BigIntegerField(default=0)

    # Override profile settings for this specific device
    min_value_override = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    max_value_override = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )
    noise_override = models.DecimalField(
        max_digits=5, decimal_places=4, null=True, blank=True
    )

    # Simulation behavior
    simulation_mode = models.CharField(
        max_length=20,
        choices=[
            ("random_walk", "Random Walk"),
            ("sine_wave", "Sine Wave"),
            ("step", "Step Function"),
            ("ramp", "Ramp"),
            ("constant", "Constant"),
            ("realistic", "Realistic (Process-based)"),
        ],
        default="realistic",
    )
    sine_period_seconds = models.PositiveIntegerField(
        default=60, help_text="Period for sine wave simulation"
    )
    ramp_rate_per_second = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Rate of change for ramp simulation",
    )

    # Fault injection
    fault_type = models.CharField(
        max_length=20,
        choices=[
            ("none", "No Fault"),
            ("stuck", "Stuck Value"),
            ("drift", "Excessive Drift"),
            ("noise", "Excessive Noise"),
            ("spike", "Random Spikes"),
            ("dead", "Dead Sensor"),
        ],
        default="none",
    )
    fault_start = models.DateTimeField(null=True, blank=True)
    fault_end = models.DateTimeField(null=True, blank=True)

    # Statistics
    messages_sent = models.BigIntegerField(default=0)
    last_published_at = models.DateTimeField(null=True, blank=True)
    last_value_change_at = models.DateTimeField(null=True, blank=True)
    error_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Simulated Device"
        verbose_name_plural = "Simulated Devices"
        ordering = ["plc", "device_id"]
        unique_together = ["plc", "device_id"]

    def __str__(self):
        return f"{self.device_id} ({self.plc.area}/{self.plc.line})"

    @property
    def mqtt_topic(self) -> str:
        """Full MQTT topic for this device's telemetry."""
        return f"{self.plc.topic_prefix}/{self.device_id}/telemetry"

    @property
    def opc_node_id(self) -> str:
        """OPC-UA node identifier for this device."""
        return f"ns=2;s={self.plc.opc_path}/{self.device_id}"

    @property
    def effective_min(self) -> Decimal:
        """Get effective minimum value (override or profile)."""
        return (
            self.min_value_override
            if self.min_value_override is not None
            else self.profile.min_value
        )

    @property
    def effective_max(self) -> Decimal:
        """Get effective maximum value (override or profile)."""
        return (
            self.max_value_override
            if self.max_value_override is not None
            else self.profile.max_value
        )

    @property
    def value_range(self) -> Decimal:
        """Calculate the value range."""
        return self.effective_max - self.effective_min

    def increment_sequence(self) -> int:
        """Increment and return the sequence number."""
        self.sequence_number += 1
        return self.sequence_number


class SimulationSession(models.Model):
    """
    A simulation session that groups device activity.
    Allows starting/stopping groups of devices together.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        PAUSED = "paused", "Paused"
        STOPPED = "stopped", "Stopped"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    # Session configuration
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING
    )
    devices = models.ManyToManyField(
        SimulatedDevice, related_name="sessions", blank=True
    )
    plcs = models.ManyToManyField(
        SimulatedPLC,
        related_name="sessions",
        blank=True,
        help_text="Include all devices from these PLCs",
    )

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    stopped_at = models.DateTimeField(null=True, blank=True)
    scheduled_start = models.DateTimeField(null=True, blank=True)
    scheduled_stop = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.PositiveIntegerField(
        null=True, blank=True, help_text="Auto-stop after this duration"
    )

    # Scenario configuration
    scenario = models.JSONField(
        default=dict, blank=True, help_text="Predefined scenario configuration"
    )

    # Statistics
    messages_sent = models.BigIntegerField(default=0)
    events_generated = models.PositiveIntegerField(default=0)
    faults_injected = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)

    # User tracking
    created_by = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Simulation Session"
        verbose_name_plural = "Simulation Sessions"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.status})"

    def start(self):
        """Start the simulation session."""
        self.status = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at", "updated_at"])

    def stop(self):
        """Stop the simulation session."""
        self.status = self.Status.STOPPED
        self.stopped_at = timezone.now()
        self.save(update_fields=["status", "stopped_at", "updated_at"])

    def pause(self):
        """Pause the simulation session."""
        self.status = self.Status.PAUSED
        self.save(update_fields=["status", "updated_at"])


class SimulationEvent(models.Model):
    """
    Events generated during simulation (alarms, threshold breaches).
    """

    class EventType(models.TextChoices):
        THRESHOLD_HIGH = "threshold_high", "High Threshold Exceeded"
        THRESHOLD_LOW = "threshold_low", "Low Threshold Exceeded"
        CRITICAL_HIGH = "critical_high", "Critical High"
        CRITICAL_LOW = "critical_low", "Critical Low"
        DEVICE_FAULT = "device_fault", "Device Fault"
        DEVICE_RECOVERY = "device_recovery", "Device Recovery"
        PLC_OFFLINE = "plc_offline", "PLC Offline"
        PLC_ONLINE = "plc_online", "PLC Online"
        RATE_OF_CHANGE = "rate_of_change", "Abnormal Rate of Change"

    class Severity(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"
        INFO = "info", "Informational"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(
        SimulatedDevice,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )
    plc = models.ForeignKey(
        SimulatedPLC,
        on_delete=models.CASCADE,
        related_name="events",
        null=True,
        blank=True,
    )
    session = models.ForeignKey(
        SimulationSession,
        on_delete=models.SET_NULL,
        related_name="events",
        null=True,
        blank=True,
    )

    event_type = models.CharField(max_length=20, choices=EventType.choices)
    severity = models.CharField(max_length=20, choices=Severity.choices)
    message = models.TextField()
    value = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    threshold = models.DecimalField(
        max_digits=12, decimal_places=4, null=True, blank=True
    )

    acknowledged = models.BooleanField(default=False)
    acknowledged_by = models.CharField(max_length=100, blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    published_to_mqtt = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Simulation Event"
        verbose_name_plural = "Simulation Events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["device", "-created_at"]),
            models.Index(fields=["severity", "-created_at"]),
            models.Index(fields=["acknowledged", "-created_at"]),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.device or self.plc}"
