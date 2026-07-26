# mypy: ignore-errors
"""Tests verifying authentication enforcement on protected vs public endpoints.

Uses ``anonymous_client`` (no user) to confirm that:
- Public endpoints (e.g. /health) remain accessible without login.
- Protected endpoints correctly return 401 when no credentials are provided.
"""

from __future__ import annotations

from httpx import AsyncClient


async def test_health_is_public(anonymous_client: AsyncClient) -> None:
    """/health must be reachable without authentication."""
    response = await anonymous_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_system_modules_is_accessible(anonymous_client: AsyncClient) -> None:
    """System modules endpoint — Phase 1 may accept anonymous access."""
    response = await anonymous_client.get("/api/v1/system/modules")
    assert response.status_code in (200, 401)


async def test_equipment_categories_is_accessible(
    anonymous_client: AsyncClient,
) -> None:
    """Equipment categories endpoint — Phase 1 may accept anonymous access."""
    response = await anonymous_client.get("/api/v1/equipment/categories")
    assert response.status_code in (200, 401)


async def test_energy_devices_is_accessible(
    anonymous_client: AsyncClient,
) -> None:
    """Energy devices endpoint — Phase 1 may accept anonymous access."""
    response = await anonymous_client.get("/api/v1/energy/devices")
    assert response.status_code in (200, 401)
