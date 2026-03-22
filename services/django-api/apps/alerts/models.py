"""
Alert models for ForgeLink.

Manages alert rules, active alerts, and alert history.
Django is the source of truth - Spring Notification Service only dispatches.
"""

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class AlertRule(models.Model):
    """
    Alert rule definition.
    Defines conditions that trigger alerts for devices.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    # Target - can be specific device, device type, or area
    device = models.ForeignKey(
        "assets.Device",
        on_delete=models.CASCADE,
        related_name="alert_rules",
        null=True,
        blank=True,
        help_text="Specific device (leave blank for type/area rules)",
    )
    device_type = models.ForeignKey(
        "assets.DeviceType",
        on_delete=models.CASCADE,
        related_name="alert_rules",
        null=True,
        blank=True,
        help_text="Apply to all devices of this type",
    )
    area_code = models.CharField(
        max_length=64, blank=True, help_text="Apply to all devices in this area"
    )

    # Rule type
    RULE_TYPES = [
        ("threshold_high", "High Threshold"),
        ("threshold_low", "Low Threshold"),
        ("threshold_range", "Out of Range"),
        ("rate_of_change", "Rate of Change"),
        ("stale_data", "Stale Data"),
        ("quality_bad", "Bad Quality"),
    ]
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)

    # Thresholds
    threshold_value = models.FloatField(
        null=True, blank=True, help_text="Threshold value for high/low rules"
    )
    threshold_low = models.FloatField(
        null=True, blank=True, help_text="Low threshold for range rules"
    )
    threshold_high = models.FloatField(
        null=True, blank=True, help_text="High threshold for range rules"
    )
    rate_threshold = models.FloatField(
        null=True, blank=True, help_text="Rate of change threshold (units/minute)"
    )
    stale_minutes = models.IntegerField(
        null=True, blank=True, help_text="Minutes before data is considered stale"
    )

    # Severity
    SEVERITIES = [
        ("critical", "Critical"),
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
        ("info", "Info"),
    ]
    severity = models.CharField(max_length=10, choices=SEVERITIES, default="medium")

    # Notification settings
    notify_slack = models.BooleanField(default=True)
    slack_channel = models.CharField(
        max_length=64,
        blank=True,
        default="#forgelink-alerts",
        help_text="Slack channel for notifications",
    )

    # Cooldown to prevent alert storms
    cooldown_minutes = models.IntegerField(
        default=5,
        validators=[MinValueValidator(1), MaxValueValidator(1440)],
        help_text="Minutes before same alert can fire again",
    )

    # Status
    is_active = models.BooleanField(default=True)

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.CharField(max_length=128, blank=True)

    class Meta:
        db_table = "alerts_rule"
        ordering = ["-severity", "name"]
        verbose_name = "Alert Rule"
        verbose_name_plural = "Alert Rules"

    def __str__(self):
        return f"{self.name} ({self.severity})"


class Alert(models.Model):
    """
    Active or recent alert instance.
    Created when an alert rule triggers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Source
    rule = models.ForeignKey(
        AlertRule, on_delete=models.SET_NULL, null=True, related_name="alerts"
    )
    device = models.ForeignKey(
        "assets.Device", on_delete=models.CASCADE, related_name="alerts"
    )

    # Alert details
    alert_type = models.CharField(max_length=20)
    severity = models.CharField(max_length=10)
    message = models.TextField()

    # Triggering data
    value = models.FloatField(null=True, blank=True)
    threshold = models.FloatField(null=True, blank=True)
    unit = models.CharField(max_length=20, blank=True)

    # Status
    STATUSES = [
        ("active", "Active"),
        ("acknowledged", "Acknowledged"),
        ("resolved", "Resolved"),
        ("suppressed", "Suppressed"),
    ]
    status = models.CharField(max_length=15, choices=STATUSES, default="active")

    # Timestamps
    triggered_at = models.DateTimeField(default=timezone.now)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    acknowledged_by = models.CharField(max_length=128, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.CharField(max_length=128, blank=True)

    # Notification tracking
    notified_slack = models.BooleanField(default=False)
    notified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "alerts_alert"
        ordering = ["-triggered_at"]
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"
        indexes = [
            models.Index(fields=["status", "-triggered_at"]),
            models.Index(fields=["device", "-triggered_at"]),
            models.Index(fields=["severity", "status"]),
        ]

    def __str__(self):
        return f"[{self.severity}] {self.device.device_id}: {self.message[:50]}"

    def acknowledge(self, user: str):
        """Acknowledge the alert."""
        self.status = "acknowledged"
        self.acknowledged_at = timezone.now()
        self.acknowledged_by = user
        self.save(update_fields=["status", "acknowledged_at", "acknowledged_by"])

    def resolve(self, user: str = "system"):
        """Resolve the alert."""
        self.status = "resolved"
        self.resolved_at = timezone.now()
        self.resolved_by = user
        self.save(update_fields=["status", "resolved_at", "resolved_by"])

    @property
    def duration_seconds(self) -> int:
        """Time since alert triggered."""
        end = self.resolved_at or timezone.now()
        return int((end - self.triggered_at).total_seconds())


class AlertHistory(models.Model):
    """
    Historical alert record for analytics.
    Alerts are moved here after resolution for long-term storage.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Original alert data
    alert_id = models.UUIDField()
    rule_id = models.UUIDField(null=True)
    device_id = models.CharField(max_length=64)
    plant = models.CharField(max_length=64)
    area = models.CharField(max_length=64)

    # Alert details
    alert_type = models.CharField(max_length=20)
    severity = models.CharField(max_length=10)
    message = models.TextField()
    value = models.FloatField(null=True)
    threshold = models.FloatField(null=True)

    # Timeline
    triggered_at = models.DateTimeField()
    acknowledged_at = models.DateTimeField(null=True)
    resolved_at = models.DateTimeField(null=True)
    duration_seconds = models.IntegerField()

    # Resolution
    acknowledged_by = models.CharField(max_length=128, blank=True)
    resolved_by = models.CharField(max_length=128, blank=True)
    resolution_notes = models.TextField(blank=True)

    # Archived timestamp
    archived_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "alerts_history"
        ordering = ["-triggered_at"]
        verbose_name = "Alert History"
        verbose_name_plural = "Alert History"
        indexes = [
            models.Index(fields=["device_id", "-triggered_at"]),
            models.Index(fields=["area", "-triggered_at"]),
            models.Index(fields=["severity", "-triggered_at"]),
        ]

    def __str__(self):
        return f"[{self.triggered_at.date()}] {self.device_id}: {self.message[:50]}"
