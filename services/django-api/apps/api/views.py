"""ForgeLink REST API Views."""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response


@api_view(["POST"])
@permission_classes([AllowAny])
def slack_webhook(request):
    """Handle Slack event callbacks."""
    # Slack URL verification challenge
    if request.data.get("type") == "url_verification":
        return Response({"challenge": request.data.get("challenge")})

    # Handle actual events
    # event = request.data.get('event', {})
    # TODO: Process Slack events based on event.get('type')

    return Response({"ok": True})
