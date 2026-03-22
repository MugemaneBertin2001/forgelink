"""Tests for core views."""

from unittest.mock import MagicMock, patch

import pytest


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check_success(self, client):
        """Test health check returns 200."""
        response = client.get("/health/")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "forgelink-api"


class TestReadinessCheck:
    """Tests for readiness check endpoint."""

    @pytest.mark.django_db
    def test_readiness_check_all_healthy(self, client):
        """Test readiness check with healthy services."""
        with (
            patch("django.db.connection.cursor") as mock_cursor,
            patch("django.core.cache.cache") as mock_cache,
            patch("apps.telemetry.tdengine.get_tdengine_connection") as mock_td,
        ):
            mock_cursor.return_value.__enter__ = MagicMock()
            mock_cursor.return_value.__exit__ = MagicMock()
            mock_cache.set.return_value = None
            mock_cache.get.return_value = "ok"
            mock_td.return_value = MagicMock()

            response = client.get("/ready/")
            data = response.json()
            assert data["service"] == "forgelink-api"

    def test_readiness_check_returns_checks(self, client):
        """Test readiness check returns checks structure."""
        response = client.get("/ready/")
        data = response.json()
        assert "checks" in data
        assert "database" in data["checks"]
        assert "redis" in data["checks"]
