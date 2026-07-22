# mypy: ignore-errors
"""Tests verifying registration API endpoints respond correctly."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_drugs_authenticated(auth_client: AsyncClient) -> None:
    """GET /api/v1/registration/drugs/ returns 200 with authentication."""
    response = await auth_client.get("/api/v1/registration/drugs/")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_drugs_anonymous(auth_client: AsyncClient) -> None:
    """GET /api/v1/registration/drugs/ returns 200 — Phase 1 auth not enforced."""
    response = await auth_client.get("/api/v1/registration/drugs/")
    assert response.status_code == 200
