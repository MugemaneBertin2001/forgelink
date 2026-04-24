"""Tests for the correlation-ID middleware and structlog wiring.

These cover the pure functions and the middleware's HTTP contract:
(1) an incoming X-Correlation-ID is reused, (2) a missing header
gets a fresh UUID, (3) the value is bound into structlog
contextvars so downstream ``structlog.get_logger`` calls see it,
and (4) the response carries the ID back for the client.
"""

from __future__ import annotations

import re
import uuid
from unittest.mock import MagicMock

import pytest
from structlog.contextvars import clear_contextvars

from apps.core.correlation import (
    HEADER_NAME,
    CorrelationIdMiddleware,
    get_correlation_id,
)

_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


@pytest.fixture(autouse=True)
def _clear_contextvars_around_each_test():
    # Contextvars leak across tests in the same process — pytest's
    # test order is not the request order our middleware expects.
    clear_contextvars()
    yield
    clear_contextvars()


class TestGetCorrelationId:
    def test_returns_none_when_nothing_bound(self):
        assert get_correlation_id() is None


class TestCorrelationIdMiddleware:
    def _build_request(self, meta=None):
        request = MagicMock()
        request.META = meta or {}
        return request

    def _build_middleware(self):
        # get_response captures the correlation_id at the time it's
        # called, then returns a dict-like response we can subscript
        # on. This lets the test assert both that the middleware
        # bound the id DURING the request AND wrote it on the way out.
        captured = {}

        def get_response(req):
            captured["during_request"] = get_correlation_id()
            response = MagicMock()
            # __setitem__ on MagicMock — use a real dict so [] works
            response._headers = {}
            response.__setitem__ = lambda self_, key, value: self_._headers.__setitem__(
                key, value
            )
            response.__getitem__ = lambda self_, key: self_._headers.__getitem__(key)
            return response

        return CorrelationIdMiddleware(get_response), captured

    def test_generates_uuid_when_header_missing(self):
        middleware, captured = self._build_middleware()
        request = self._build_request()

        response = middleware(request)

        assert _UUID_RE.match(captured["during_request"])
        assert response[HEADER_NAME] == captured["during_request"]
        assert request.correlation_id == captured["during_request"]

    def test_reuses_incoming_header(self):
        incoming = "11111111-2222-3333-4444-555555555555"
        middleware, captured = self._build_middleware()
        request = self._build_request({"HTTP_X_CORRELATION_ID": incoming})

        response = middleware(request)

        assert captured["during_request"] == incoming
        assert response[HEADER_NAME] == incoming

    def test_clears_contextvars_between_requests(self):
        """A long-lived worker must not leak one request's ID into the next."""
        incoming = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        middleware, _ = self._build_middleware()
        middleware(self._build_request({"HTTP_X_CORRELATION_ID": incoming}))

        # After the first request returns, the contextvar is still
        # bound (asgi/wsgi workers don't tear the context down). The
        # middleware itself clears at the START of the next request —
        # not the end — so this assertion is the explicit contract:
        # next_request() must not inherit the previous id.
        next_middleware, next_captured = self._build_middleware()
        next_middleware(self._build_request())

        assert next_captured["during_request"] != incoming
        assert _UUID_RE.match(next_captured["during_request"])

    def test_bound_id_is_uuid4_shape(self):
        middleware, captured = self._build_middleware()
        middleware(self._build_request())

        # The middleware uses uuid.uuid4() — version byte is 4.
        parsed = uuid.UUID(captured["during_request"])
        assert parsed.version == 4
