# mypy: ignore-errors
"""Research module test fixtures."""

from __future__ import annotations

import pytest


@pytest.fixture
def sample_project_data():
    return {
        "project_no": "PROJ-2026-001",
        "name": "阿莫西林工艺优化",
        "stage": "立项",
        "status": "进行中",
    }
