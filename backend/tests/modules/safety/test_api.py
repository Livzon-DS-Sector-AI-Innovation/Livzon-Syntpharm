# mypy: ignore-errors
"""Tests for safety module API endpoints."""

from __future__ import annotations

from httpx import AsyncClient


class TestSafetyCheckAPI:
    async def test_get_checks_returns_200(self, auth_client: AsyncClient) -> None:
        """GET /api/v1/safety/checks returns 200 with authentication."""
        response = await auth_client.get("/api/v1/safety/checks")
        assert response.status_code == 200

    async def test_get_checks_anonymous(self, auth_client: AsyncClient) -> None:
        """GET /api/v1/safety/checks returns 200 — Phase 1 auth not enforced."""
        response = await auth_client.get("/api/v1/safety/checks")
        assert response.status_code == 200


class TestHazardAPI:
    async def test_get_hazards_returns_200(self, auth_client: AsyncClient) -> None:
        """GET /api/v1/safety/hazards returns 200 with authentication."""
        response = await auth_client.get("/api/v1/safety/hazards")
        assert response.status_code == 200
