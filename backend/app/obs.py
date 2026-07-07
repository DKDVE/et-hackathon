"""Structured JSON logging + per-request timing (D-016 scope for M5).

One JSON line per log record; one line per HTTP request with latency and, where
derivable from the path, ``dossier_id`` / ``event_id`` correlation fields. This
is the groundwork the M6 ``reasoning_runs`` tracing (migration 0003) will share:
the correlation-id scheme lives here, not in the reasoning layer.

No external observability stack (LangSmith/OTel) — D-016: observability is our
own database plus these logs. Zero new services, zero network.
"""

from __future__ import annotations

import json
import logging
import re
import time
from contextvars import ContextVar
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Correlation fields propagated for the duration of one request (contextvars are
# task-safe under async). Populated by the middleware, read by the JSON formatter.
# Default is None (never a shared mutable); readers coerce to an empty dict.
_correlation: ContextVar[dict[str, Any] | None] = ContextVar("_correlation", default=None)


def _current() -> dict[str, Any]:
    return _correlation.get() or {}

_EVENT_ID_RE = re.compile(r"/api/events/(\d+)")
_DOSSIER_ID_RE = re.compile(r"/api/dossiers/(\d+)")

_RESERVED = set(
    logging.makeLogRecord({}).__dict__
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    """Render each record as a single JSON line, folding in correlation context
    and any ``extra=`` fields passed to the logging call."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
        }
        payload.update(_current())
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, separators=(",", ":"))


def configure_logging(level: int = logging.INFO) -> None:
    """Install the JSON formatter on the root logger (idempotent)."""
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    # Replace any pre-existing handlers so we never double-log.
    root.handlers = [handler]
    # uvicorn owns its access log; ours is the structured request line below.
    logging.getLogger("uvicorn.access").disabled = True


def _correlation_from_path(path: str) -> dict[str, int]:
    fields: dict[str, int] = {}
    if m := _EVENT_ID_RE.search(path):
        fields["event_id"] = int(m.group(1))
    if m := _DOSSIER_ID_RE.search(path):
        fields["dossier_id"] = int(m.group(1))
    return fields


class TimingMiddleware:
    """Pure-ASGI request timing + correlation (safe with SSE streaming, unlike
    BaseHTTPMiddleware which buffers streamed bodies). One structured line per
    request with method, path, status and latency."""

    _log = logging.getLogger("oce.request")

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        token = _correlation.set(_correlation_from_path(path))
        start = time.perf_counter()
        status = 500

        async def send_wrapper(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            self._log.info(
                "request",
                extra={
                    "method": scope.get("method", ""),
                    "path": path,
                    "status": status,
                    "latency_ms": elapsed_ms,
                },
            )
            _correlation.reset(token)


def set_correlation(**fields: Any) -> None:
    """Merge extra correlation fields into the current request scope (e.g. the
    dossier_id created by POST /events/{id}/dossier, which the path lacks)."""
    current = dict(_current())
    current.update({k: v for k, v in fields.items() if v is not None})
    _correlation.set(current)
