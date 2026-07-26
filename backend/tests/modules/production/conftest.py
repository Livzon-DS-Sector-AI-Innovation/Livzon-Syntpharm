# mypy: ignore-errors
"""Production module test fixtures."""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.main import app
from app.modules.production.schemas import (
    BatchCreate,
    ProcessSpecCreate,
    ProductionPlanCreate,
)
from app.platform.identity.deps import get_current_user
from app.platform.identity.models import User


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
def sample_batch_create(sample_batch_data) -> BatchCreate:
    return BatchCreate(**sample_batch_data)


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


@pytest.fixture
def sample_plan_create(sample_production_plan_data) -> ProductionPlanCreate:
    return ProductionPlanCreate(**sample_production_plan_data)


@pytest.fixture
def sample_process_spec_data():
    uid = uuid.uuid4().hex[:8]
    return {
        "spec_code": f"SPEC-{uid}",
        "product_code": "PROD-001",
        "spec_name": "阿莫西林生产工艺规程",
        "version": "V1.0",
    }


@pytest.fixture
def sample_process_spec_create(sample_process_spec_data) -> ProcessSpecCreate:
    return ProcessSpecCreate(**sample_process_spec_data)


@pytest.fixture
def sample_process_step_data():
    return {
        "step_no": 1,
        "step_name": "发酵",
        "sequence_order": 1,
    }


@pytest.fixture
def sample_plan_task_data():
    return {
        "product_code": "PROD-001",
        "batch_qty": 10,
    }


@pytest.fixture
def sample_production_record_data():
    return {
        "record_no": "REC-001",
        "operation_type": "material_add",
    }


@pytest.fixture
async def auth_client(db_session) -> AsyncIterator[AsyncClient]:
    """Authenticated client with unique user per test."""
    emp_no = f"EMP-{uuid.uuid4().hex[:8]}"
    user = User(name="Test User", employee_no=emp_no)
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    async def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    async def _override_get_current_user():
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
    await db_session.rollback()
