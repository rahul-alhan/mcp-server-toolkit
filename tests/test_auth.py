"""Smoke tests for the bearer-auth middleware on the HTTP transport.

These don't spin up uvicorn — we mount the middleware in front of a tiny
Starlette app and drive it with httpx.ASGITransport, which is fast and
deterministic.
"""
from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from mcp_server.auth import BearerAuthMiddleware


TOKEN = "test-token-please-rotate"


def _build_app():
    async def hello(request):
        return PlainTextResponse("ok")

    base = Starlette(routes=[Route("/ping", hello)])
    base.add_middleware(BearerAuthMiddleware, expected_token=TOKEN)
    return base


@pytest.mark.asyncio
async def test_missing_authorization_returns_401():
    app = _build_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://t") as c:
        r = await c.get("/ping")
    assert r.status_code == 401
    assert r.json() == {"error": "unauthorized"}


@pytest.mark.asyncio
async def test_non_bearer_scheme_returns_401():
    app = _build_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://t") as c:
        r = await c.get("/ping", headers={"authorization": f"Basic {TOKEN}"})
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_wrong_bearer_token_returns_403():
    app = _build_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://t") as c:
        r = await c.get("/ping", headers={"authorization": "Bearer not-the-right-token"})
    assert r.status_code == 403
    assert r.json() == {"error": "forbidden"}


@pytest.mark.asyncio
async def test_correct_bearer_token_passes_through():
    app = _build_app()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app), base_url="http://t") as c:
        r = await c.get("/ping", headers={"authorization": f"Bearer {TOKEN}"})
    assert r.status_code == 200
    assert r.text == "ok"


def test_middleware_rejects_empty_token_at_construction():
    base = Starlette()
    with pytest.raises(ValueError):
        BearerAuthMiddleware(base, expected_token="")
