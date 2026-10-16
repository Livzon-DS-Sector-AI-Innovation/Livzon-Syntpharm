# mypy: ignore-errors
"""Registration module test fixtures."""

from __future__ import annotations

from datetime import date

import pytest


@pytest.fixture
def sample_drug_data():
    return {
        "name": "阿莫西林",
        "type": "仿制药",
        "acceptance_date": date(2026, 1, 15),
        "current_node": 0,
    }
