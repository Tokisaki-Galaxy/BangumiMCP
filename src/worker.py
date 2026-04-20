"""Cloudflare Python Worker entrypoint for the public Bangumi MCP service."""

from __future__ import annotations

from functools import cache
import sys
from pathlib import Path
from typing import Optional

SOURCE_DIR = Path(__file__).resolve().parent
if str(SOURCE_DIR) not in sys.path:
    sys.path.insert(0, str(SOURCE_DIR))

from server import get_mcp
from utils.request_auth import (
    extract_bearer_token,
    reset_request_bangumi_token,
    reset_request_bangumi_public_mode,
    set_request_bangumi_token,
    set_request_bangumi_public_mode,
)

try:
    from workers import WorkerEntrypoint
except ImportError:  # pragma: no cover - local import fallback
    class WorkerEntrypoint:  # type: ignore[override]
        """Fallback base class for local import-time validation."""

        def __init__(self, env=None):
            self.env = env


class AuthorizationContextMiddleware:
    """Bind the caller's Bearer token to the request context."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        public_mode_handle = set_request_bangumi_public_mode(True)
        header_token = _get_header(scope.get("headers", []), b"authorization")
        request_token = extract_bearer_token(header_token)
        if request_token is None:
            request_token = _get_header(scope.get("headers", []), b"authtoken")
            if request_token is not None:
                request_token = request_token.strip() or None
        token_handle = set_request_bangumi_token(request_token)

        try:
            await self.app(scope, receive, send)
        finally:
            reset_request_bangumi_token(token_handle)
            reset_request_bangumi_public_mode(public_mode_handle)


def _get_header(headers, key: bytes) -> Optional[str]:
    for header_key, header_value in headers:
        if header_key.lower() == key:
            return header_value.decode("latin-1")
    return None


@cache
def get_public_mcp_app():
    return AuthorizationContextMiddleware(get_mcp().streamable_http_app())


class Default(WorkerEntrypoint):
    async def fetch(self, request):
        import asgi

        return await asgi.fetch(get_public_mcp_app(), request.js_object, self.env)
