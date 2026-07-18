"""Tests for the X-API-Key authentication dependency."""

import pytest
from fastapi import HTTPException

from packages.server.api.auth import verify_api_key
from packages.server.config import settings


async def test_valid_key_passes(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "s3cret")
    assert await verify_api_key("s3cret") is None


async def test_wrong_key_rejected(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "s3cret")
    with pytest.raises(HTTPException) as exc:
        await verify_api_key("wrong")
    assert exc.value.status_code == 401


async def test_missing_header_rejected(monkeypatch):
    monkeypatch.setattr(settings, "api_key", "s3cret")
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(None)
    assert exc.value.status_code == 401


async def test_production_without_key_fails_closed(monkeypatch):
    monkeypatch.setattr(settings, "api_key", None)
    monkeypatch.setattr(settings, "environment", "production")
    with pytest.raises(HTTPException) as exc:
        await verify_api_key(None)
    assert exc.value.status_code == 503


async def test_development_without_key_allows(monkeypatch):
    monkeypatch.setattr(settings, "api_key", None)
    monkeypatch.setattr(settings, "environment", "development")
    assert await verify_api_key(None) is None


def test_all_api_routes_require_auth_except_health():
    """Every /api/v1/* route except health must carry the auth dependency."""
    from fastapi.routing import APIRoute

    from packages.server.main import app

    unprotected = [
        route.path
        for route in app.routes
        if isinstance(route, APIRoute)
        and route.path.startswith("/api/v1")
        and not route.path.startswith("/api/v1/health")
        and not any(
            dep.call is verify_api_key for dep in route.dependant.dependencies
        )
    ]
    assert unprotected == []
