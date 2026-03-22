"""Tests for core middleware."""

import json
import time
from unittest.mock import MagicMock, patch

import pytest
from django.http import JsonResponse
from django.test import RequestFactory

from apps.core.middleware import (
    AuditMiddleware,
    JWTAuthenticationMiddleware,
    RateLimitMiddleware,
)


@pytest.fixture
def request_factory():
    """Create request factory."""
    return RequestFactory()


@pytest.fixture
def get_response():
    """Mock get_response callable."""

    def _response(request):
        return JsonResponse({"ok": True})

    return _response


class TestJWTAuthenticationMiddleware:
    """Tests for JWT authentication middleware."""

    def test_public_path_skips_auth(self, request_factory, get_response):
        """Test that public paths skip authentication."""
        middleware = JWTAuthenticationMiddleware(get_response)
        request = request_factory.get("/health/")

        response = middleware(request)
        assert response.status_code == 200

    def test_no_token_passes_through(self, request_factory, get_response):
        """Test that requests without tokens pass through."""
        middleware = JWTAuthenticationMiddleware(get_response)
        request = request_factory.get("/api/test/")

        response = middleware(request)
        assert response.status_code == 200

    def test_expired_token_returns_401(self, request_factory, get_response):
        """Test that expired tokens return 401."""
        import jwt

        middleware = JWTAuthenticationMiddleware(get_response)

        # Mock _validate_token to raise ExpiredSignatureError
        with patch.object(
            middleware, "_validate_token", side_effect=jwt.ExpiredSignatureError()
        ):
            request = request_factory.get("/api/test/")
            request.META["HTTP_AUTHORIZATION"] = "Bearer expired_token"

            response = middleware(request)
            assert response.status_code == 401

    def test_invalid_token_returns_401(self, request_factory, get_response):
        """Test that invalid tokens return 401."""
        import jwt

        middleware = JWTAuthenticationMiddleware(get_response)

        with patch.object(
            middleware, "_validate_token", side_effect=jwt.InvalidTokenError()
        ):
            request = request_factory.get("/api/test/")
            request.META["HTTP_AUTHORIZATION"] = "Bearer invalid_token"

            response = middleware(request)
            assert response.status_code == 401

    def test_extract_token_from_header(self, request_factory, get_response):
        """Test token extraction from Authorization header."""
        middleware = JWTAuthenticationMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.META["HTTP_AUTHORIZATION"] = "Bearer test_token_123"

        token = middleware._extract_token(request)
        assert token == "test_token_123"

    def test_no_bearer_prefix(self, request_factory, get_response):
        """Test that tokens without Bearer prefix are ignored."""
        middleware = JWTAuthenticationMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.META["HTTP_AUTHORIZATION"] = "test_token_123"

        token = middleware._extract_token(request)
        assert token is None

    def test_is_public_path(self, request_factory, get_response):
        """Test public path detection."""
        middleware = JWTAuthenticationMiddleware(get_response)

        assert middleware._is_public_path("/health/") is True
        assert middleware._is_public_path("/ready/") is True
        assert middleware._is_public_path("/metrics") is True
        assert middleware._is_public_path("/admin/login/") is True
        assert middleware._is_public_path("/api/alerts/") is False


class TestRateLimitMiddleware:
    """Tests for rate limiting middleware."""

    def test_health_check_skips_rate_limit(self, request_factory, get_response):
        """Test that health checks skip rate limiting."""
        middleware = RateLimitMiddleware(get_response)
        request = request_factory.get("/health/")

        response = middleware(request)
        assert response.status_code == 200

    def test_rate_limit_not_exceeded(self, request_factory, get_response, mock_cache):
        """Test normal request within rate limit."""
        middleware = RateLimitMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        # Mock cache to return value below limit
        mock_cache.get.return_value = 10

        response = middleware(request)
        assert response.status_code == 200

    def test_user_rate_limit_exceeded(self, request_factory, get_response):
        """Test rate limit exceeded returns 429."""
        middleware = RateLimitMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.jwt_payload = {"sub": "user123"}

        # Mock cache at module level
        with patch("apps.core.middleware.cache") as mock_cache:
            mock_cache.get.return_value = 60
            response = middleware(request)
            # When cache reports limit reached, should return 429
            assert response.status_code == 429

    def test_endpoint_rate_limit_exceeded(self, request_factory, get_response):
        """Test endpoint rate limit exceeded returns 429."""
        middleware = RateLimitMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        # Mock cache - first call for user (not exceeded), second for endpoint (exceeded)
        with patch("apps.core.middleware.cache") as mock_cache:
            mock_cache.get.side_effect = [10, 600]
            response = middleware(request)
            assert response.status_code == 429

    def test_get_user_id_from_jwt(self, request_factory, get_response):
        """Test getting user ID from JWT payload."""
        middleware = RateLimitMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.jwt_payload = {"sub": "user123"}

        user_id = middleware._get_user_id(request)
        assert user_id == "user123"

    def test_get_user_id_from_ip(self, request_factory, get_response):
        """Test getting user ID from IP when no JWT."""
        middleware = RateLimitMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        user_id = middleware._get_user_id(request)
        assert user_id == "192.168.1.1"


class TestAuditMiddleware:
    """Tests for audit middleware."""

    def test_get_request_skips_audit(self, request_factory, get_response):
        """Test that GET requests skip auditing."""
        middleware = AuditMiddleware(get_response)
        request = request_factory.get("/api/test/")

        with patch("apps.audit.tasks.create_audit_log") as mock_audit:
            response = middleware(request)
            mock_audit.delay.assert_not_called()

        assert response.status_code == 200

    def test_health_check_skips_audit(self, request_factory, get_response):
        """Test that health checks skip auditing."""
        middleware = AuditMiddleware(get_response)
        request = request_factory.post("/health/", {})

        with patch("apps.audit.tasks.create_audit_log") as mock_audit:
            response = middleware(request)
            mock_audit.delay.assert_not_called()

    def test_post_request_creates_audit(self, request_factory, get_response):
        """Test that POST requests create audit logs."""
        middleware = AuditMiddleware(get_response)
        request = request_factory.post(
            "/api/alerts/", data={}, content_type="application/json"
        )
        request.META["REMOTE_ADDR"] = "127.0.0.1"
        request.META["HTTP_USER_AGENT"] = "Test Agent"

        with patch("apps.audit.tasks.create_audit_log") as mock_audit:
            response = middleware(request)
            mock_audit.delay.assert_called_once()

        assert response.status_code == 200

    def test_audit_includes_user_info(self, request_factory, get_response):
        """Test that audit includes user information."""
        middleware = AuditMiddleware(get_response)
        request = request_factory.post("/api/test/", {})
        request.jwt_payload = {"sub": "user123", "email": "user@test.com", "role": "OPERATOR"}
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        with patch("apps.audit.tasks.create_audit_log") as mock_audit:
            middleware(request)
            call_kwargs = mock_audit.delay.call_args[1]
            assert call_kwargs["user_id"] == "user123"
            assert call_kwargs["role_code"] == "OPERATOR"

    def test_parse_resource_extracts_type(self, request_factory, get_response):
        """Test resource type extraction from path."""
        middleware = AuditMiddleware(get_response)

        resource_type, resource_id = middleware._parse_resource("/api/alerts/123/")
        assert resource_type == "Alert"
        assert resource_id == "123"

    def test_parse_resource_no_id(self, request_factory, get_response):
        """Test resource parsing when no ID present."""
        middleware = AuditMiddleware(get_response)

        resource_type, resource_id = middleware._parse_resource("/api/alerts/")
        assert resource_type == "Alert"
        assert resource_id is None

    def test_get_client_ip_with_proxy(self, request_factory, get_response):
        """Test getting client IP with X-Forwarded-For header."""
        middleware = AuditMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.META["HTTP_X_FORWARDED_FOR"] = "10.0.0.1, 192.168.1.1"

        ip = middleware._get_client_ip(request)
        assert ip == "10.0.0.1"

    def test_get_client_ip_direct(self, request_factory, get_response):
        """Test getting client IP without proxy."""
        middleware = AuditMiddleware(get_response)
        request = request_factory.get("/api/test/")
        request.META["REMOTE_ADDR"] = "192.168.1.1"

        ip = middleware._get_client_ip(request)
        assert ip == "192.168.1.1"

    def test_acknowledge_action_detected(self, request_factory, get_response):
        """Test that acknowledge action is properly detected."""
        middleware = AuditMiddleware(get_response)
        request = request_factory.post("/api/alerts/123/acknowledge/", {})
        request.META["REMOTE_ADDR"] = "127.0.0.1"

        with patch("apps.audit.tasks.create_audit_log") as mock_audit:
            middleware(request)
            call_kwargs = mock_audit.delay.call_args[1]
            assert call_kwargs["action"] == "acknowledge"
