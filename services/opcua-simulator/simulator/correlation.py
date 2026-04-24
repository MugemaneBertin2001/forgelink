"""Correlation-ID propagation for the OPC-UA simulation server.

Every Redis pub/sub message that triggers a ``handle_value_update``
gets a fresh UUID4 so the sub-second-density log lines produced
around each update (node lookup, quality translation, write) can
be grouped by a single ID when debugging a specific device.

Django can also embed a ``correlation_id`` field in the Redis
payload — if present, it's honored; otherwise we mint a fresh one.
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
