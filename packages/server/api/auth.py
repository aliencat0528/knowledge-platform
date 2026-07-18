"""API key authentication dependency."""

import secrets

from fastapi import Header, HTTPException

from ..config import settings


async def verify_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
) -> None:
    """Require a valid X-API-Key header when authentication is enabled.

    Behavior:
    - API_KEY configured: every protected endpoint must send a matching X-API-Key.
    - API_KEY missing in production: fail closed (503) so a public deployment
      never runs unauthenticated by accident.
    - API_KEY missing in development: allow (local usage).
    """
    if settings.api_key:
        if x_api_key is None or not secrets.compare_digest(x_api_key, settings.api_key):
            raise HTTPException(status_code=401, detail="Invalid or missing API key")
        return

    if settings.is_production:
        raise HTTPException(
            status_code=503,
            detail="API_KEY is not configured; refusing unauthenticated access in production",
        )
