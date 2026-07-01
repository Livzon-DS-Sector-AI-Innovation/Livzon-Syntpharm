"""Warehouse module test fixtures."""

from __future__ import annotations

import uuid

import pytest


@pytest.fixture
def sample_inventory_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "code": f"MAT-{uid}",
        "name": "原料药A",
        "spec": "0.5g",
        "unit": "kg",
        "available": 100.0,
        "safety": 50.0,
        "last_month": 80.0,
        "two_months_ago": 90.0,
        "today_balance": 100.0,
        "import_key": f"test-import-{uid}",
    }
