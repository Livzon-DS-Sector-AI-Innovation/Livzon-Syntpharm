"""Production module test fixtures."""

from __future__ import annotations

import uuid

import pytest


@pytest.fixture
def sample_batch_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "batch_no": f"BATCH-{uid}",
        "product_code": "PROD-001",
        "product_name": "阿莫西林",
        "specification": "0.5g",
        "unit": "kg",
        "status": "draft",
        "planned_qty": 100.0,
    }


@pytest.fixture
def sample_production_plan_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "plan_no": f"PLAN-{uid}",
        "plan_name": "7月生产计划",
        "plan_type": "月计划",
        "plan_month": "2026-07",
        "status": "draft",
        "total_batches": 10,
    }
