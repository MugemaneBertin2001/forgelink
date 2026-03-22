"""ForgeLink REST API Views."""

import hashlib
import hmac
import logging
import time

from django.conf import settings

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


def verify_slack_signature(request) -> bool:
    """Verify Slack request signature using signing secret."""
    signing_secret = getattr(settings, "SLACK_SIGNING_SECRET", None)
    if not signing_secret:
        logger.warning("SLACK_SIGNING_SECRET not configured, skipping verification")
        return True

    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")

    if not timestamp or not signature:
        return False

    # Reject requests older than 5 minutes
    if abs(time.time() - int(timestamp)) > 60 * 5:
        return False

    # Calculate expected signature
    sig_basestring = f"v0:{timestamp}:{request.body.decode('utf-8')}"
    expected_sig = (
        "v0="
        + hmac.new(
            signing_secret.encode("utf-8"),
            sig_basestring.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected_sig, signature)


@api_view(["POST"])
@permission_classes([AllowAny])
def slack_webhook(request):
    """Handle Slack event callbacks.

    Processes incoming Slack events for interactive actions
    like alert acknowledgement from Slack messages.
    """
    # Verify Slack signature
    if not verify_slack_signature(request):
        logger.warning("Invalid Slack signature")
        return Response({"error": "Invalid signature"}, status=401)

    # Slack URL verification challenge
    if request.data.get("type") == "url_verification":
        return Response({"challenge": request.data.get("challenge")})

    # Handle interactive callbacks (button clicks)
    if request.data.get("type") == "interactive_message":
        return _handle_interactive_message(request.data)

    # Handle block actions (newer Slack block kit)
    if request.data.get("type") == "block_actions":
        return _handle_block_actions(request.data)

    # Handle event callbacks
    if request.data.get("type") == "event_callback":
        event = request.data.get("event", {})
        event_type = event.get("type")

        if event_type == "app_mention":
            return _handle_app_mention(event)
        elif event_type == "message":
            return _handle_message_event(event)

    return Response({"ok": True})


def _handle_interactive_message(data: dict) -> Response:
    """Handle legacy interactive message callbacks."""
    actions = data.get("actions", [])
    user = data.get("user", {})
    callback_id = data.get("callback_id", "")

    for action in actions:
        action_value = action.get("value", "")

        if callback_id.startswith("alert_"):
            alert_id = callback_id.replace("alert_", "")
            if action_value == "acknowledge":
                _acknowledge_alert_from_slack(alert_id, user.get("name", "slack_user"))
            elif action_value == "resolve":
                _resolve_alert_from_slack(alert_id, user.get("name", "slack_user"))

    return Response({"ok": True})


def _handle_block_actions(data: dict) -> Response:
    """Handle block kit interactive actions."""
    from apps.alerts.models import Alert

    actions = data.get("actions", [])
    user = data.get("user", {})
    username = user.get("username", user.get("name", "slack_user"))

    for action in actions:
        action_id = action.get("action_id", "")
        value = action.get("value", "")

        if action_id == "acknowledge_alert":
            _acknowledge_alert_from_slack(value, username)
        elif action_id == "resolve_alert":
            _resolve_alert_from_slack(value, username)
        elif action_id == "view_alert":
            # Just acknowledge viewing, no action needed
            logger.info(f"User {username} viewed alert {value}")

    return Response({"ok": True})


def _acknowledge_alert_from_slack(alert_id: str, username: str) -> None:
    """Acknowledge an alert triggered from Slack interaction."""
    from apps.alerts.models import Alert

    try:
        alert = Alert.objects.get(id=alert_id)
        if alert.status == "active":
            alert.acknowledge(user=f"slack:{username}")
            logger.info(f"Alert {alert_id} acknowledged by {username} via Slack")
    except Alert.DoesNotExist:
        logger.warning(f"Alert {alert_id} not found for acknowledgement")
    except Exception as e:
        logger.error(f"Failed to acknowledge alert {alert_id}: {e}")


def _resolve_alert_from_slack(alert_id: str, username: str) -> None:
    """Resolve an alert triggered from Slack interaction."""
    from apps.alerts.models import Alert

    try:
        alert = Alert.objects.get(id=alert_id)
        if alert.status != "resolved":
            alert.resolve(user=f"slack:{username}")
            logger.info(f"Alert {alert_id} resolved by {username} via Slack")
    except Alert.DoesNotExist:
        logger.warning(f"Alert {alert_id} not found for resolution")
    except Exception as e:
        logger.error(f"Failed to resolve alert {alert_id}: {e}")


def _handle_app_mention(event: dict) -> Response:
    """Handle @app mentions in Slack channels."""
    channel = event.get("channel")
    user = event.get("user")
    text = event.get("text", "").lower()

    logger.info(f"App mentioned by {user} in {channel}: {text}")

    # Respond to specific commands
    if "status" in text:
        _send_status_summary(channel)
    elif "alerts" in text or "active" in text:
        _send_active_alerts_summary(channel)

    return Response({"ok": True})


def _handle_message_event(event: dict) -> Response:
    """Handle direct messages to the bot."""
    # Only handle DMs (channel type = "im")
    channel_type = event.get("channel_type")
    if channel_type != "im":
        return Response({"ok": True})

    text = event.get("text", "").lower()
    channel = event.get("channel")

    if "help" in text:
        _send_help_message(channel)

    return Response({"ok": True})


def _send_status_summary(channel: str) -> None:
    """Send plant status summary to Slack channel."""
    from apps.alerts.models import Alert
    from apps.assets.models import Device

    try:
        active_alerts = Alert.objects.filter(status="active").count()
        critical_alerts = Alert.objects.filter(
            status="active", severity="critical"
        ).count()
        online_devices = Device.objects.filter(status="online").count()
        total_devices = Device.objects.filter(is_active=True).count()

        logger.info(
            f"Status summary requested for {channel}: "
            f"{active_alerts} active alerts, {online_devices}/{total_devices} devices online"
        )
    except Exception as e:
        logger.error(f"Failed to generate status summary: {e}")


def _send_active_alerts_summary(channel: str) -> None:
    """Send active alerts summary to Slack channel."""
    from apps.alerts.models import Alert

    try:
        alerts = Alert.objects.filter(status="active").select_related(
            "device", "rule"
        )[:10]

        logger.info(f"Active alerts summary requested for {channel}: {alerts.count()}")
    except Exception as e:
        logger.error(f"Failed to generate alerts summary: {e}")


def _send_help_message(channel: str) -> None:
    """Send help message with available commands."""
    logger.info(f"Help message requested for {channel}")
