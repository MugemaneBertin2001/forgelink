"""Correlation-ID propagation for the MQTT → Kafka bridge.

The bridge is the first hop where telemetry enters the IT side of
the stack, so every MQTT message gets a fresh UUID4 correlation
ID which is:

1. Attached to the outgoing Kafka message as an ``x-correlation-id``
   header — Django's telemetry consumer reads this and continues
   the trace.
2. Bound into the stdlib ``logging`` context via a LogRecord filter
   so the per-message log lines all carry the same ID (helps when
   grepping ``docker compose logs``).

We do not currently honor a correlation_id embedded in the MQTT
payload by the producing device — device firmware doesn't set one
today. If/when it does, lift it here in preference to UUID4.
"""

from __future__ import annotations

import logging
import threading
import uuid
from typing import Optional

KAFKA_HEADER = "x-correlation-id"

_context = threading.local()


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def bind(correlation_id: str) -> None:
    _context.correlation_id = correlation_id


def clear() -> None:
    if hasattr(_context, "correlation_id"):
        del _context.correlation_id


def get() -> Optional[str]:
    return getattr(_context, "correlation_id", None)


class CorrelationIdFilter(logging.Filter):
    """Inject the current correlation_id (or '-') into every LogRecord."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get() or "-"
        return True
