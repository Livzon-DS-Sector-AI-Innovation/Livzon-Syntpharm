# mypy: ignore-errors
from __future__ import annotations

import uuid

import pytest

from app.core.exceptions import DuplicateException, NotFoundException
from app.modules.production.schemas import (
    BatchCreate,
    BatchUpdate,
    ProductionPlanCreate,
    ProductionPlanUpdate,
    ProcessSpecCreate,
    ProcessSpecUpdate,
    ProcessStepCreate,
    PlanTaskCreate,
    ProductionRecordCreate,
)
from app.modules.production.service import ProductionService


@pytest.fixture
def svc(db_session):
    return ProductionService(session=db_session)


# ============ Batch Operations ============


@pytest.mark.asyncio
async def test_create_batch(svc, sample_batch_create):
    batch = await svc.create_batch(sample_batch_create)
    assert batch.batch_no == sample_batch_create.batch_no
    assert batch.product_code == "PROD-001"


@pytest.mark.asyncio
async def test_get_batch_not_found(svc):
    batch = await svc.get_batch(uuid.uuid4())
    assert batch is None


@pytest.mark.asyncio
async def test_update_batch(svc, sample_batch_create):
    created = await svc.create_batch(sample_batch_create)
    update = BatchUpdate(batch_no="BATCH-UPDATED")
    updated = await svc.update_batch(created.id, update)
    assert updated.batch_no == "BATCH-UPDATED"


@pytest.mark.asyncio
async def test_delete_batch(svc, sample_batch_create):
    created = await svc.create_batch(sample_batch_create)
    result = await svc.delete_batch(created.id)
    assert result is True

    deleted = await svc.get_batch(created.id)
    assert deleted is None


@pytest.mark.asyncio
async def test_list_batches(svc, sample_batch_create):
    await svc.create_batch(sample_batch_create)
    items, total = await svc.get_batches()
    assert total >= 1


# ============ BatchMaterial Operations ============


@pytest.mark.asyncio
async def test_add_batch_material(svc, sample_batch_create):
    batch = await svc.create_batch(sample_batch_create)
    mat = await svc.add_batch_material(batch.id, {
        "material_code": "MAT-001",
        "material_name": "原料A",
        "planned_qty": 50.0,
        "unit": "kg",
    })
    assert mat.material_code == "MAT-001"


@pytest.mark.asyncio
async def test_get_batch_materials(svc, sample_batch_create):
    batch = await svc.create_batch(sample_batch_create)
    await svc.add_batch_material(batch.id, {
        "material_code": "MAT-001",
        "material_name": "原料A",
        "planned_qty": 50.0,
        "unit": "kg",
    })
    materials = await svc.get_batch_materials(batch.id)
    assert len(materials) >= 1


# ============ ProductionPlan Operations ============


@pytest.mark.asyncio
async def test_create_plan(svc, sample_plan_create):
    plan = await svc.create_plan(sample_plan_create)
    assert plan.plan_name == "7月生产计划"


@pytest.mark.asyncio
async def test_get_plan_not_found(svc):
    plan = await svc.get_plan(uuid.uuid4())
    assert plan is None


@pytest.mark.asyncio
async def test_update_plan(svc, sample_plan_create):
    created = await svc.create_plan(sample_plan_create)
    update = ProductionPlanUpdate(plan_name="更新后计划")
    updated = await svc.update_plan(created.id, update)
    assert updated.plan_name == "更新后计划"


@pytest.mark.asyncio
async def test_delete_plan(svc, sample_plan_create):
    created = await svc.create_plan(sample_plan_create)
    result = await svc.delete_plan(created.id)
    assert result is True


# ============ PlanTask Operations ============


@pytest.mark.asyncio
async def test_create_task(svc, sample_plan_create, sample_plan_task_data):
    plan = await svc.create_plan(sample_plan_create)
    task = await svc.create_task(PlanTaskCreate(
        plan_id=plan.id,
        **sample_plan_task_data,
    ))
    assert task.product_code == "PROD-001"


@pytest.mark.asyncio
async def test_get_tasks(svc, sample_plan_create, sample_plan_task_data):
    plan = await svc.create_plan(sample_plan_create)
    await svc.create_task(PlanTaskCreate(
        plan_id=plan.id,
        **sample_plan_task_data,
    ))
    tasks = await svc.get_tasks(plan.id)
    assert len(tasks) >= 1


# ============ ProcessSpec Operations ============


@pytest.mark.asyncio
async def test_create_process_spec(svc, sample_process_spec_create):
    spec = await svc.create_process_spec(sample_process_spec_create)
    assert spec.product_code == "PROD-001"


@pytest.mark.asyncio
async def test_get_process_spec_not_found(svc):
    spec = await svc.get_process_spec(uuid.uuid4())
    assert spec is None


@pytest.mark.asyncio
async def test_delete_process_spec(svc, sample_process_spec_create):
    created = await svc.create_process_spec(sample_process_spec_create)
    result = await svc.delete_process_spec(created.id)
    assert result is True


# ============ ProcessStep Operations ============


@pytest.mark.asyncio
async def test_create_process_step(svc, sample_process_spec_create, sample_process_step_data):
    spec = await svc.create_process_spec(sample_process_spec_create)
    step = await svc.create_process_step(ProcessStepCreate(
        spec_id=spec.id,
        **sample_process_step_data,
    ))
    assert step.step_name == "发酵"


# ============ ProductionRecord Operations ============


@pytest.mark.asyncio
async def test_create_production_record(svc, sample_batch_create, sample_production_record_data):
    batch = await svc.create_batch(sample_batch_create)
    record = await svc.create_production_record(ProductionRecordCreate(
        batch_id=batch.id,
        **sample_production_record_data,
    ))
    assert record.record_no == "REC-001"
