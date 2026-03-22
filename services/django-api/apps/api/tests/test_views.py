"""Tests for API views."""

import json
import time
from unittest.mock import patch

from django.test import RequestFactory
from rest_framework.test import APIClient

import pytest

from apps.api.views import (
    _acknowledge_alert_from_slack,
    _resolve_alert_from_slack,
    verify_slack_signature,
)


@pytest.fixture
def api_client():
    """Create API client."""
    return APIClient()


@pytest.fixture
def request_factory():
    """Create request factory."""
    return RequestFactory()


class TestSlackSignatureVerification:
    """Tests for Slack signature verification."""

    def test_no_signing_secret_skips_verification(self, request_factory):
        """Test that missing signing secret skips verification."""
        request = request_factory.post(
            "/api/webhooks/slack/",
            data=json.dumps({"type": "url_verification"}),
            content_type="application/json",
        )

        with patch("apps.api.views.settings") as mock_settings:
            mock_settings.SLACK_SIGNING_SECRET = None
            result = verify_slack_signature(request)
            assert result is True

    def test_missing_headers_fails_verification(self, request_factory):
        """Test that missing headers fail verification."""
        request = request_factory.post(
            "/api/webhooks/slack/",
            data=json.dumps({"type": "test"}),
            content_type="application/json",
        )

        with patch("apps.api.views.settings") as mock_settings:
            mock_settings.SLACK_SIGNING_SECRET = "test_secret"
            result = verify_slack_signature(request)
            assert result is False

    def test_old_timestamp_fails_verification(self, request_factory):
        """Test that old timestamps fail verification."""
        request = request_factory.post(
            "/api/webhooks/slack/",
            data=json.dumps({"type": "test"}),
            content_type="application/json",
        )
        request.META["HTTP_X_SLACK_REQUEST_TIMESTAMP"] = str(int(time.time()) - 400)
        request.META["HTTP_X_SLACK_SIGNATURE"] = "v0=fake"

        with patch("apps.api.views.settings") as mock_settings:
            mock_settings.SLACK_SIGNING_SECRET = "test_secret"
            result = verify_slack_signature(request)
            assert result is False


class TestSlackWebhook:
    """Tests for Slack webhook endpoint."""

    def test_url_verification_challenge(self, api_client):
        """Test Slack URL verification challenge response."""
        data = {
            "type": "url_verification",
            "challenge": "test_challenge_123",
        }

        with patch("apps.api.views.verify_slack_signature", return_value=True):
            response = api_client.post(
                "/api/webhooks/slack/",
                data=data,
                format="json",
            )

        assert response.status_code == 200
        assert response.data["challenge"] == "test_challenge_123"

    def test_invalid_signature_returns_401(self, api_client):
        """Test that invalid signature returns 401."""
        data = {"type": "event_callback"}

        with patch("apps.api.views.verify_slack_signature", return_value=False):
            response = api_client.post(
                "/api/webhooks/slack/",
                data=data,
                format="json",
            )

        assert response.status_code == 401

    def test_block_actions_acknowledge(self, api_client):
        """Test block action for acknowledging alert."""
        data = {
            "type": "block_actions",
            "user": {"username": "testuser", "name": "Test User"},
            "actions": [
                {
                    "action_id": "acknowledge_alert",
                    "value": "test-alert-id",
                }
            ],
        }

        with (
            patch("apps.api.views.verify_slack_signature", return_value=True),
            patch("apps.api.views._acknowledge_alert_from_slack") as mock_ack,
        ):
            response = api_client.post(
                "/api/webhooks/slack/",
                data=data,
                format="json",
            )

        assert response.status_code == 200
        mock_ack.assert_called_once_with("test-alert-id", "testuser")

    def test_block_actions_resolve(self, api_client):
        """Test block action for resolving alert."""
        data = {
            "type": "block_actions",
            "user": {"username": "testuser"},
            "actions": [
                {
                    "action_id": "resolve_alert",
                    "value": "test-alert-id",
                }
            ],
        }

        with (
            patch("apps.api.views.verify_slack_signature", return_value=True),
            patch("apps.api.views._resolve_alert_from_slack") as mock_resolve,
        ):
            response = api_client.post(
                "/api/webhooks/slack/",
                data=data,
                format="json",
            )

        assert response.status_code == 200
        mock_resolve.assert_called_once_with("test-alert-id", "testuser")


@pytest.mark.django_db
class TestSlackAlertActions:
    """Tests for Slack alert action handlers."""

    def test_acknowledge_alert_success(self, alert):
        """Test acknowledging alert from Slack."""
        _acknowledge_alert_from_slack(str(alert.id), "slack_user")

        alert.refresh_from_db()
        assert alert.status == "acknowledged"
        assert "slack:slack_user" in alert.acknowledged_by

    def test_acknowledge_nonexistent_alert(self):
        """Test acknowledging nonexistent alert."""
        # Should not raise, just log warning
        _acknowledge_alert_from_slack("nonexistent-id", "slack_user")

    def test_resolve_alert_success(self, alert):
        """Test resolving alert from Slack."""
        _resolve_alert_from_slack(str(alert.id), "slack_user")

        alert.refresh_from_db()
        assert alert.status == "resolved"
        assert "slack:slack_user" in alert.resolved_by

    def test_resolve_nonexistent_alert(self):
        """Test resolving nonexistent alert."""
        # Should not raise, just log warning
        _resolve_alert_from_slack("nonexistent-id", "slack_user")
