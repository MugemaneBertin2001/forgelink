"""ForgeLink REST API URLs."""
from django.urls import path, include

from apps.api.views import slack_webhook

urlpatterns = [
    # Webhooks
    path("webhooks/slack/", slack_webhook, name="slack-webhook"),

    # Simulator API
    path("simulator/", include("apps.simulator.urls")),

    # Telemetry API
    path("telemetry/", include("apps.telemetry.urls")),

    # Assets API
    path("assets/", include("apps.assets.urls")),

    # Alerts API
    path("alerts/", include("apps.alerts.urls")),
]
