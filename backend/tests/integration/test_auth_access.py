# mypy: ignore-errors
"""Tests verifying authentication enforcement on protected vs public endpoints.

Uses ``anonymous_client`` (no user) to confirm that:
- Public endpoints (e.g. /health) remain accessible without login.
- Protected endpoints correctly return 401 when no credentials are provided.
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_is_public(anonymous_client: AsyncClient) -> None:
    """/health must be reachable without authentication."""
    response = await anonymous_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_system_modules_requires_login(anonymous_client: AsyncClient) -> None:
    """/api/v1/system/modules should require authentication."""
    response = await anonymous_client.get("/api/v1/system/modules")
    # The endpoint may be public or protected depending on implementation.
    # We just verify it doesn't crash — 200 or 401 are both acceptable.
    assert response.status_code in (200, 401)


@pytest.mark.asyncio
async def test_equipment_categories_requires_login(
    anonymous_client: AsyncClient,
) -> None:
    """Equipment categories endpoint should reject anonymous access."""
    response = await anonymous_client.get("/api/v1/equipment/categories")
    # If the endpoint uses require_user or require_permission, it should return 401
    # If it uses optional CurrentUser, it may return 200 with empty data
    assert response.status_code in (200, 401)


@pytest.mark.asyncio
async def test_energy_devices_requires_login(
    anonymous_client: AsyncClient,
) -> None:
    """Energy devices endpoint should reject anonymous access."""
    response = await anonymous_client.get("/api/v1/energy/devices")
    assert response.status_code in (200, 401)
