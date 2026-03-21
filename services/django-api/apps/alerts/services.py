"""
Alert services for ForgeLink.

Handles alert rule evaluation and notification dispatch.
"""

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from django.conf import settings
from django.db import models
from django.utils import timezone as dj_timezone

from confluent_kafka import Producer

from .models import Alert, AlertHistory, AlertRule

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Run async coroutine from sync context."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


class AlertService:
    """
    Service for alert management and evaluation.
    """

    _kafka_producer: Optional[Producer] = None

    @classmethod
    def get_kafka_producer(cls) -> Producer:
        """Get or create Kafka producer."""
        if cls._kafka_producer is None:
            cls._kafka_producer = Producer(
                {
                    "bootstrap.servers": settings.KAFKA_BOOTSTRAP_SERVERS,
                    "client.id": "forgelink-alert-service",
                }
            )
        return cls._kafka_producer

    @staticmethod
    def evaluate_threshold(
        device_id: str, value: float, quality: str = "good"
    ) -> List[Alert]:
        """
        Evaluate threshold rules for a device reading.

        Returns list of triggered alerts.
        """
        from apps.assets.models import Device

        try:
            device = Device.objects.select_related(
                "device_type", "cell__line__area"
            ).get(device_id=device_id)
        except Device.DoesNotExist:
            logger.warning(f"Device not found: {device_id}")
            return []

        area = device.cell.line.area
        triggered_alerts = []

        # Find applicable rules
        rules = AlertRule.objects.filter(is_active=True).filter(
            # Device-specific, type-specific, or area-specific
            models.Q(device=device)
            | models.Q(device_type=device.device_type, device__isnull=True)
            | models.Q(
                area_code=area.code, device__isnull=True, device_type__isnull=True
            )
        )

        for rule in rules:
            alert = AlertService._evaluate_rule(rule, device, value, quality)
            if alert:
                triggered_alerts.append(alert)

        return triggered_alerts

    @staticmethod
    def _evaluate_rule(
        rule: AlertRule, device, value: float, quality: str
    ) -> Optional[Alert]:
        """Evaluate a single rule against a value."""

        # Check cooldown - don't fire if recent alert exists
        recent_cutoff = dj_timezone.now() - timedelta(minutes=rule.cooldown_minutes)
        recent_alert = Alert.objects.filter(
            rule=rule,
            device=device,
            triggered_at__gte=recent_cutoff,
            status__in=["active", "acknowledged"],
        ).exists()

        if recent_alert:
            return None

        triggered = False
        message = ""
        threshold = None

        if rule.rule_type == "threshold_high" and rule.threshold_value is not None:
            if value >= rule.threshold_value:
                triggered = True
                threshold = rule.threshold_value
                message = f"Value {value:.2f} exceeds high threshold {threshold:.2f}"

        elif rule.rule_type == "threshold_low" and rule.threshold_value is not None:
            if value <= rule.threshold_value:
                triggered = True
                threshold = rule.threshold_value
                message = f"Value {value:.2f} below low threshold {threshold:.2f}"

        elif rule.rule_type == "threshold_range":
            if rule.threshold_low is not None and value < rule.threshold_low:
                triggered = True
                threshold = rule.threshold_low
                message = f"Value {value:.2f} below range minimum {threshold:.2f}"
            elif rule.threshold_high is not None and value > rule.threshold_high:
                triggered = True
                threshold = rule.threshold_high
                message = f"Value {value:.2f} above range maximum {threshold:.2f}"

        elif rule.rule_type == "quality_bad":
            if quality == "bad":
                triggered = True
                message = "Device reporting bad quality data"

        if triggered:
            alert = Alert.objects.create(
                rule=rule,
                device=device,
                alert_type=rule.rule_type,
                severity=rule.severity,
                message=message,
                value=value,
                threshold=threshold,
                unit=device.effective_unit,
            )

            logger.info(f"Alert triggered: {alert.id} - {message}")

            # Send to Slack via Kafka
            if rule.notify_slack:
                AlertService.send_to_slack(alert, rule.slack_channel)

            # Broadcast via Socket.IO for in-app notifications
            AlertService.broadcast_new_alert(alert)

            return alert

        return None

    @staticmethod
    def send_to_slack(alert: Alert, channel: str = "#forgelink-alerts"):
        """
        Publish alert to Kafka for Slack notification.
        """
        try:
            device = alert.device
            area = device.cell.line.area

            event = {
                "alertId": str(alert.id),
                "deviceId": device.device_id,
                "deviceName": device.name,
                "plant": area.plant.code,
                "area": area.code,
                "alertType": alert.alert_type,
                "severity": alert.severity,
                "message": alert.message,
                "value": alert.value,
                "threshold": alert.threshold,
                "unit": alert.unit,
                "timestamp": alert.triggered_at.isoformat(),
                "slackChannel": channel,
            }

            producer = AlertService.get_kafka_producer()
            producer.produce(
                topic="alerts.notifications",
                key=str(alert.id),
                value=json.dumps(event),
                callback=AlertService._delivery_callback,
            )
            producer.poll(0)  # Trigger callbacks

            alert.notified_slack = True
            alert.notified_at = dj_timezone.now()
            alert.save(update_fields=["notified_slack", "notified_at"])

            logger.info(f"Alert sent to Kafka: {alert.id}")

        except Exception as e:
            logger.error(f"Failed to send alert to Kafka: {e}")

    @staticmethod
    def _delivery_callback(err, msg):
        """Kafka delivery callback."""
        if err:
            logger.error(f"Kafka delivery failed: {err}")
        else:
            logger.debug(f"Kafka delivery success: {msg.topic()}/{msg.partition()}")

    @staticmethod
    def broadcast_new_alert(alert: Alert):
        """
        Broadcast new alert via Socket.IO for in-app notifications.
        """
        try:
            from .socketio import broadcast_new_alert

            device = alert.device
            area = device.cell.line.area

            alert_data = {
                "alert_id": str(alert.id),
                "device_id": device.device_id,
                "device_name": device.name,
                "area": area.code,
                "plant": area.plant.code,
                "severity": alert.severity,
                "status": alert.status,
                "message": alert.message,
                "value": alert.value,
                "threshold": alert.threshold,
                "unit": alert.unit,
                "triggered_at": alert.triggered_at.isoformat(),
            }

            _run_async(broadcast_new_alert(alert_data))
            logger.debug(f"Broadcast new alert via Socket.IO: {alert.id}")

        except Exception as e:
            logger.warning(f"Failed to broadcast alert via Socket.IO: {e}")

    @staticmethod
    def _broadcast_alert_resolved(alert: Alert, area_code: str):
        """Broadcast alert resolution via Socket.IO."""
        try:
            from .socketio import broadcast_alert_resolved

            alert_data = {
                "alert_id": str(alert.id),
                "device_id": alert.device.device_id,
                "area": area_code,
                "status": "resolved",
                "resolved_by": alert.resolved_by,
                "resolved_at": alert.resolved_at.isoformat(),
                "duration_seconds": alert.duration_seconds,
            }

            _run_async(broadcast_alert_resolved(alert_data))
            logger.debug(f"Broadcast alert resolved via Socket.IO: {alert.id}")

        except Exception as e:
            logger.warning(f"Failed to broadcast resolution via Socket.IO: {e}")

    @staticmethod
    def acknowledge_alert(alert_id: str, user: str) -> Optional[Alert]:
        """Acknowledge an alert."""
        try:
            alert = Alert.objects.get(id=alert_id, status="active")
            alert.acknowledge(user)
            logger.info(f"Alert acknowledged: {alert_id} by {user}")
            return alert
        except Alert.DoesNotExist:
            return None

    @staticmethod
    def resolve_alert(
        alert_id: str, user: str = "system", notes: str = ""
    ) -> Optional[Alert]:
        """Resolve an alert and archive to history."""
        try:
            alert = Alert.objects.select_related("device__cell__line__area__plant").get(
                id=alert_id, status__in=["active", "acknowledged"]
            )
            alert.resolve(user)

            # Archive to history
            device = alert.device
            area = device.cell.line.area

            AlertHistory.objects.create(
                alert_id=alert.id,
                rule_id=alert.rule_id,
                device_id=device.device_id,
                plant=area.plant.code,
                area=area.code,
                alert_type=alert.alert_type,
                severity=alert.severity,
                message=alert.message,
                value=alert.value,
                threshold=alert.threshold,
                triggered_at=alert.triggered_at,
                acknowledged_at=alert.acknowledged_at,
                resolved_at=alert.resolved_at,
                duration_seconds=alert.duration_seconds,
                acknowledged_by=alert.acknowledged_by,
                resolved_by=alert.resolved_by,
                resolution_notes=notes,
            )

            logger.info(f"Alert resolved and archived: {alert_id}")

            # Broadcast resolution via Socket.IO
            AlertService._broadcast_alert_resolved(alert, area.code)

            return alert

        except Alert.DoesNotExist:
            return None

    @staticmethod
    def get_active_alerts(
        area: Optional[str] = None, severity: Optional[str] = None, limit: int = 100
    ) -> List[Alert]:
        """Get active alerts with optional filters."""
        queryset = Alert.objects.filter(
            status__in=["active", "acknowledged"]
        ).select_related("device", "rule")

        if area:
            queryset = queryset.filter(device__cell__line__area__code=area)

        if severity:
            queryset = queryset.filter(severity=severity)

        return list(queryset[:limit])

    @staticmethod
    def get_alert_stats(hours: int = 24) -> Dict[str, Any]:
        """Get alert statistics for dashboard."""
        cutoff = dj_timezone.now() - timedelta(hours=hours)

        alerts = Alert.objects.filter(triggered_at__gte=cutoff)

        by_severity = {}
        for sev in ["critical", "high", "medium", "low", "info"]:
            by_severity[sev] = alerts.filter(severity=sev).count()

        by_status = {}
        for status in ["active", "acknowledged", "resolved"]:
            by_status[status] = alerts.filter(status=status).count()

        return {
            "period_hours": hours,
            "total": alerts.count(),
            "active": alerts.filter(status="active").count(),
            "by_severity": by_severity,
            "by_status": by_status,
        }
