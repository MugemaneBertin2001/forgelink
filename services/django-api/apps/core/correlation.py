"""Correlation ID middleware + structlog setup for cross-service tracing.

Every log line, every outgoing Kafka message, and every downstream
HTTP call carries an ``X-Correlation-ID`` so we can reconstruct the
causal chain of a single user action across:

    Flutter / curl  ──┐
                     ──►  Django API  ──► Kafka (alerts.notifications)
                          │                ├─► Spring Notification ─► Slack
                          │                │                        └─► Email
                          └─► Spring IDP (JWT validation, JWKS)

**The rule:** if we receive an X-Correlation-ID header, we reuse it.
If not, we generate a UUID4 at the edge. Once bound, every
``structlog.get_logger(...)`` call in the request scope includes it.
Kafka producers should read from ``get_correlation_id()`` and add
the value to message headers so consumers can continue the chain.

Why we don't use OpenTelemetry traceparent for this: trace_id is a
128-bit hex blob optimized for collection systems, not humans
grepping logs. X-Correlation-ID is a short UUID a support engineer
can paste into Kibana / Grafana Loki and find every line.
"""

from __future__ import annotations

import uuid
from typing import Optional

import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars, get_contextvars

HEADER_NAME = "X-Correlation-ID"
_META_KEY = "HTTP_X_CORRELATION_ID"
# Kafka header keys are bytes — fixed here so producer + consumer agree.
KAFKA_HEADER = b"x-correlation-id"


def get_correlation_id() -> Optional[str]:
    """Return the correlation ID bound to the current context, or None."""
    return get_contextvars().get("correlation_id")


class CorrelationIdMiddleware:
    """Bind X-Correlation-ID into structlog context for the request.

    Must run AFTER ``structlog`` is configured but BEFORE anything
    that logs (auth, rate-limit, audit). In settings.MIDDLEWARE it
    sits directly after PrometheusBeforeMiddleware so metrics and
    logs share the same trace.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Incoming header (from Flutter app, from a curl, from an
        # upstream proxy) takes precedence so a whole user flow
        # shares one ID. Otherwise mint a fresh UUID4.
        correlation_id = request.META.get(_META_KEY) or str(uuid.uuid4())

        # Contextvars are isolated per asyncio task / request, so
        # we MUST clear at the start. Without this, a long-lived
        # worker would leak IDs from one request to the next.
        clear_contextvars()
        bind_contextvars(correlation_id=correlation_id)
        request.correlation_id = correlation_id

        response = self.get_response(request)

        # Mirror the ID back on the response so clients (Flutter,
        # curl with -v) can report it when filing an issue.
        response[HEADER_NAME] = correlation_id
        return response


def configure_structlog() -> None:
    """Initialize structlog processors for the whole process.

    Called from AppConfig.ready so it runs once at worker startup
    rather than per-request. Safe to call multiple times — the
    reconfiguration is idempotent.
    """
    structlog.configure(
        processors=[
            # merge_contextvars — pulls correlation_id (and any
            # other bound vars) into every log event.
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
