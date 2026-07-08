"""HTTP Basic access gate for the hosted Render instance (M15 / D-025).

When ``ACCESS_PASSWORD`` is set, every route except ``/health`` requires HTTP
Basic auth (any username, that password). Unset → middleware is inert; local
demo and ``make demo-gate`` are unchanged.

Why it exists: the hosted instance exposes unauthenticated writes (event intake,
review-queue verdicts). This is not RBAC — a single shared password on the
closing slide is the MVP scope (NFR-8 roadmap: SSO/RBAC).
"""

from __future__ import annotations

import base64
import binascii
from secrets import compare_digest

from urllib.parse import parse_qs

from starlette.types import ASGIApp, Receive, Scope, Send

from app.config import get_settings

_REALM = "OCE"


def _parse_basic(auth_header: str) -> tuple[str, str] | None:
    if not auth_header.lower().startswith("basic "):
        return None
    try:
        raw = base64.b64decode(auth_header.split(" ", 1)[1].strip(), validate=True)
    except (binascii.Error, IndexError, ValueError):
        return None
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None
    if ":" not in decoded:
        return None
    user, password = decoded.split(":", 1)
    return user, password


async def _unauthorized(send: Send) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"www-authenticate", f'Basic realm="{_REALM}"'.encode()),
                (b"content-type", b"text/plain; charset=utf-8"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": b"Unauthorized", "more_body": False})


class AccessGateMiddleware:
    """Pure-ASGI gate — safe with SSE (no BaseHTTPMiddleware buffering)."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        password = get_settings().access_password
        if not password:
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path == "/health" or scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        headers = {k.lower(): v for k, v in scope.get("headers", [])}
        auth = headers.get(b"authorization", b"").decode("latin-1")
        creds = _parse_basic(auth)
        if creds is not None and compare_digest(creds[1], password):
            await self.app(scope, receive, send)
            return

        # ponytail: EventSource and window.open cannot send Authorization headers
        qs = parse_qs(scope.get("query_string", b"").decode("latin-1"))
        if qs.get("access", [""])[0] == password:
            await self.app(scope, receive, send)
            return

        await _unauthorized(send)
