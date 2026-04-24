"""Correlation-ID propagation for the OPC-UA → MQTT gateway.

The gateway is upstream of the MQTT bridge; we mint a UUID per
``datachange_notification`` and bind it into structlog contextvars
so every log line for that change (dead-band check, sequence
increment, publish, buffer) shares the same trace ID.

We don't yet forward the ID into the MQTT message itself — MQTT 5
user properties would be the channel, and EMQX + paho-mqtt both
support them, but the mqtt-bridge also has to read them back out,
which is a change for its own PR. Today the mqtt-bridge mints its
own UUID per received message; breaking that chain is explicit
tech debt tracked in the OT↔IT observability story.
"""

from __future__ import annotations

import uuid
from typing import Optional

from structlog.contextvars import (
    bind_contextvars,
    clear_contextvars,
    get_contextvars,
)


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def bind(correlation_id: str) -> None:
    bind_contextvars(correlation_id=correlation_id)


def clear() -> None:
    clear_contextvars()


def get() -> Optional[str]:
    return get_contextvars().get("correlation_id")
