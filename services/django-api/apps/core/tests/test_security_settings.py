"""Pin the Django production security posture.

These tests load ``apps.core.settings`` under controlled env-var
combinations and assert the settings module produces the headers and
cookie flags a production review would demand. Anyone relaxing a
security default later must either break a test or refactor it —
silent drift is blocked.
"""

import importlib
import os
import sys

import pytest


def _reload_settings(env_overrides: dict):
    """Reload apps.core.settings with a fresh env snapshot.

    Django settings are module-level side effects: once imported, the
    computed values (SECURE_HSTS_SECONDS, SOCKETIO CORS, etc.) are
    frozen. For this test we clear and re-populate the relevant
    DJANGO_* env vars, then force-reload the module.
    """
    tracked = [
        "DJANGO_DEBUG",
        "DJANGO_SECRET_KEY",
        "DJANGO_ALLOWED_HOSTS",
        "DJANGO_CSRF_TRUSTED_ORIGINS",
    ]
    saved = {k: os.environ.get(k) for k in tracked}
    try:
        for k in tracked:
            os.environ.pop(k, None)
        for k, v in env_overrides.items():
            os.environ[k] = v
        # Ensure the module is re-executed top-to-bottom so the
        # conditional `if not DEBUG:` hardening block actually runs.
        if "apps.core.settings" in sys.modules:
            del sys.modules["apps.core.settings"]
        return importlib.import_module("apps.core.settings")
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        if "apps.core.settings" in sys.modules:
            del sys.modules["apps.core.settings"]


class TestInsecureDefaultGuard:
    """Booting with DEBUG=False + the default SECRET_KEY must fail loud."""

    def test_default_secret_with_debug_false_raises(self):
        from django.core.exceptions import ImproperlyConfigured

        with pytest.raises(ImproperlyConfigured, match="insecure default"):
            _reload_settings({"DJANGO_DEBUG": "False"})

    def test_default_secret_with_debug_true_is_allowed(self):
        # Local dev should stay cheap: no-env-vars developer still boots.
        settings = _reload_settings({"DJANGO_DEBUG": "True"})
        assert settings.DEBUG is True

    def test_non_default_secret_with_debug_false_is_allowed(self):
        settings = _reload_settings(
            {
                "DJANGO_DEBUG": "False",
                "DJANGO_SECRET_KEY": "k8K2n9p3Q8rF7sL1Xw0cY5hBj4dE6gV9",
            }
        )
        assert settings.DEBUG is False
        assert settings.SECRET_KEY.startswith("k8K2n9")


class TestProductionHeaders:
    """In prod mode every hardening header must be present and correct."""

    @pytest.fixture
    def settings(self):
        return _reload_settings(
            {
                "DJANGO_DEBUG": "False",
                "DJANGO_SECRET_KEY": "prod-test-secret-abcdef123456",
            }
        )

    def test_hsts_one_year(self, settings):
        assert settings.SECURE_HSTS_SECONDS >= 60 * 60 * 24 * 365
        assert settings.SECURE_HSTS_INCLUDE_SUBDOMAINS is True

    def test_ssl_redirect_enabled(self, settings):
        assert settings.SECURE_SSL_REDIRECT is True

    def test_proxy_ssl_header_configured(self, settings):
        # Ingress terminates TLS; Django receives HTTP internally —
        # this header is how it learns the real scheme was HTTPS.
        assert settings.SECURE_PROXY_SSL_HEADER == (
            "HTTP_X_FORWARDED_PROTO",
            "https",
        )

    def test_cookies_secure(self, settings):
        assert settings.SESSION_COOKIE_SECURE is True
        assert settings.CSRF_COOKIE_SECURE is True
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_content_sniffing_blocked(self, settings):
        assert settings.SECURE_CONTENT_TYPE_NOSNIFF is True

    def test_clickjacking_deny(self, settings):
        assert settings.X_FRAME_OPTIONS == "DENY"

    def test_referrer_policy(self, settings):
        # strict-origin-when-cross-origin keeps same-origin paths readable
        # while stripping path+query on cross-origin downgrades.
        assert settings.SECURE_REFERRER_POLICY == "strict-origin-when-cross-origin"


class TestDebugModeLeavesHeadersOff:
    """DEBUG=True keeps cookie-secure / SSL-redirect off so local http
    dev works without fiddling. Tests here just confirm the production
    knobs don't leak into the debug path."""

    @pytest.fixture
    def settings(self):
        return _reload_settings({"DJANGO_DEBUG": "True"})

    def test_ssl_redirect_not_set(self, settings):
        assert getattr(settings, "SECURE_SSL_REDIRECT", False) is False

    def test_cookies_not_forced_secure(self, settings):
        # The attrs are unset in dev; getattr falls back to False.
        assert getattr(settings, "SESSION_COOKIE_SECURE", False) is False
        assert getattr(settings, "CSRF_COOKIE_SECURE", False) is False


class TestSocketIoCorsNoWildcard:
    """The Socket.IO namespace must never be *-open on web clients."""

    def test_wildcard_not_in_allowed_origins(self):
        settings = _reload_settings({"DJANGO_DEBUG": "True"})
        assert "*" not in settings.SOCKETIO["CORS_ALLOWED_ORIGINS"], (
            "Socket.IO CORS must not include '*'. A wildcard allows "
            "any origin to open a WebSocket from a logged-in user's "
            "browser and receive their alerts."
        )
