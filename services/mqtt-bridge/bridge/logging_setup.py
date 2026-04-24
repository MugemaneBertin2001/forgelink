"""Structured logging bootstrap for the MQTT bridge.

Produces JSON-per-line log output with ``correlation_id`` merged in
from structlog contextvars, matching the shape Django emits. The
``ProcessorFormatter`` path routes plain ``logging.getLogger(...)``
calls through the same pipeline so every third-party library
(paho, confluent-kafka) comes out as JSON too.

Call :func:`configure` exactly once, as early as possible in
``__main__``, before any module does its first ``log.info``.
"""

from __future__ import annotations

import logging
import sys

import structlog


def configure(level: str = "INFO") -> None:
    """Wire structlog + stdlib logging to emit JSON with correlation IDs."""
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        timestamper,
    ]

    structlog.configure(
        processors=shared_processors
        + [structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            structlog.processors.JSONRenderer(),
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    # Replace any prior handlers (basicConfig or tests) so we don't
    # double-log with two formats.
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
