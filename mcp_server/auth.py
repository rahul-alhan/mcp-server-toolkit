"""Bearer-token middleware for the HTTP/SSE transport.

Importable on its own so the auth contract can be tested without spinning
up the full FastMCP server.
"""
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests that don't carry `Authorization: Bearer <expected_token>`.

    - missing / non-Bearer Authorization header → 401
    - Bearer with wrong token                   → 403
    - Bearer with correct token                 → pass through
    """

    def __init__(self, app, expected_token: str):
        if not expected_token:
            raise ValueError("expected_token must be a non-empty string")
        super().__init__(app)
        self.expected_token = expected_token

    async def dispatch(self, request, call_next):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            return JSONResponse({"error": "unauthorized"}, status_code=401)
        token = header.removeprefix("Bearer ").strip()
        if token != self.expected_token:
            return JSONResponse({"error": "forbidden"}, status_code=403)
        return await call_next(request)
