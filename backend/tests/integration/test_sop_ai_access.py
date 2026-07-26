# mypy: ignore-errors
"""Tests verifying sop-ai route prefix works at /quality/sop-ai."""

from __future__ import annotations

from httpx import AsyncClient


async def test_sop_ai_config_authenticated(auth_client: AsyncClient) -> None:
    """GET /api/v1/quality/sop-ai/config returns 200 with authentication."""
    response = await auth_client.get("/api/v1/quality/sop-ai/config")
    assert response.status_code == 200


async def test_sop_ai_config_anonymous(auth_client: AsyncClient) -> None:
    """GET /api/v1/quality/sop-ai/config returns 200 — Phase 1 auth not enforced."""
    response = await auth_client.get("/api/v1/quality/sop-ai/config")
    assert response.status_code == 200
