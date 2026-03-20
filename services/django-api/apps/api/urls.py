"""ForgeLink REST API URLs."""
from django.urls import path

from apps.api.views import slack_webhook

urlpatterns = [
    path("webhooks/slack/", slack_webhook, name="slack-webhook"),
]
