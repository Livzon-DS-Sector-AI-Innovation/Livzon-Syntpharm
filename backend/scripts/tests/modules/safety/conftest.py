# mypy: ignore-errors
"""Safety module test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_hazard_data():
    return {
        "hazard_no": "HAZ-2026-001",
        "title": "化学品泄漏风险",
        "description": "存储区域存在泄漏风险",
        "risk_level": 2,
        "location": "化学品仓库A",
        "status": "open",
    }
