"""Correlation-ID propagation for the MQTT → Kafka bridge.

The bridge is the first hop where telemetry enters the IT side of
the stack, so every MQTT message gets a fresh UUID4 correlation
ID which is:

1. Attached to the outgoing Kafka message as an ``x-correlation-id``
   header — Django's telemetry consumer reads this and continues
   the trace.
2. Bound into structlog contextvars so the per-message log lines
   all carry the same ID (helps when grepping
   ``docker compose logs``).

We use structlog's contextvars module (rather than our own
threading.local) so the same ``merge_contextvars`` processor
Django already uses renders the field identically on both sides.

We do not currently honor a correlation_id embedded in the MQTT
payload by the producing device — device firmware doesn't set one
today. If/when it does, lift it here in preference to UUID4.
"""

from __future__ import annotations

import uuid
from typing import Optional

from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
    get_contextvars,
)

KAFKA_HEADER = "x-correlation-id"


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def bind(correlation_id: str) -> None:
    bind_contextvars(correlation_id=correlation_id)


def clear() -> None:
    clear_contextvars()


def get() -> Optional[str]:
    return get_contextvars().get("correlation_id")
