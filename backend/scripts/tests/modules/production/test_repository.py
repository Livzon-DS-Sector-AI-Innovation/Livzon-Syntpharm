# mypy: ignore-errors
from __future__ import annotations

import pytest

from app.modules.production.repository import ProductionRepository


@pytest.fixture
def repo(db_session):
    return ProductionRepository(session=db_session)


# ============ Batch Operations ============


async def test_create_and_get_batch(repo, sample_batch_data):
    created = await repo.create_batch(sample_batch_data)
    assert created.id is not None
    assert created.batch_no == sample_batch_data["batch_no"]

    fetched = await repo.get_batch_by_id(created.id)
    assert fetched is not None
    assert fetched.product_code == "PROD-001"


async def test_get_batch_not_found(repo):
    import uuid

    result = await repo.get_batch_by_id(uuid.uuid4())
    assert result is None


async def test_list_batches(repo, sample_batch_data):
    await repo.create_batch(sample_batch_data)
    items, total = await repo.get_batches(skip=0, limit=20)
    assert total >= 1
    assert len(items) >= 1


async def test_list_batches_with_filters(repo, sample_batch_data):
    await repo.create_batch(sample_batch_data)
    items, total = await repo.get_batches(skip=0, limit=20, status="draft")
    assert total >= 1


async def test_update_batch(repo, sample_batch_data):
    created = await repo.create_batch(sample_batch_data)
    updated = await repo.update_batch(created.id, {"batch_no": "BATCH-UPDATED"})
    assert updated.batch_no == "BATCH-UPDATED"


async def test_delete_batch(repo, sample_batch_data):
    created = await repo.create_batch(sample_batch_data)
    result = await repo.delete_batch(created.id)
    assert result is True
    fetched = await repo.get_batch_by_id(created.id)
    assert fetched is None


# ============ BatchMaterial Operations ============


async def test_create_batch_material(repo, sample_batch_data):
    batch = await repo.create_batch(sample_batch_data)
    mat_data = {
        "batch_id": batch.id,
        "material_code": "MAT-001",
        "material_name": "原料A",
        "planned_qty": 50.0,
        "unit": "kg",
    }
    mat = await repo.create_batch_material(mat_data)
    assert mat.material_code == "MAT-001"


async def test_get_batch_materials(repo, sample_batch_data):
    batch = await repo.create_batch(sample_batch_data)
    await repo.create_batch_material(
        {
            "batch_id": batch.id,
            "material_code": "MAT-001",
            "material_name": "原料A",
            "planned_qty": 50.0,
            "unit": "kg",
        }
    )
    materials = await repo.get_batch_materials(batch.id)
    assert len(materials) >= 1


# ============ ProductionPlan Operations ============


async def test_create_and_get_plan(repo, sample_production_plan_data):
    created = await repo.create_plan(sample_production_plan_data)
    assert created.id is not None

    fetched = await repo.get_plan_by_id(created.id)
    assert fetched is not None
    assert fetched.plan_name == "7月生产计划"


async def test_get_plan_not_found(repo):
    import uuid

    result = await repo.get_plan_by_id(uuid.uuid4())
    assert result is None


async def test_list_plans(repo, sample_production_plan_data):
    await repo.create_plan(sample_production_plan_data)
    items, total = await repo.get_plans(skip=0, limit=20)
    assert total >= 1


async def test_update_plan(repo, sample_production_plan_data):
    created = await repo.create_plan(sample_production_plan_data)
    updated = await repo.update_plan(created.id, {"plan_name": "更新后的计划"})
    assert updated.plan_name == "更新后的计划"


async def test_delete_plan(repo, sample_production_plan_data):
    created = await repo.create_plan(sample_production_plan_data)
    result = await repo.delete_plan(created.id)
    assert result is True


# ============ ProcessSpec Operations ============


async def test_create_and_get_process_spec(repo, sample_process_spec_data):
    created = await repo.create_process_spec(sample_process_spec_data)
    assert created.id is not None

    fetched = await repo.get_process_spec_by_id(created.id)
    assert fetched is not None
    assert fetched.product_code == "PROD-001"


async def test_list_process_specs(repo, sample_process_spec_data):
    await repo.create_process_spec(sample_process_spec_data)
    items, total = await repo.get_process_specs(skip=0, limit=20)
    assert total >= 1


async def test_delete_process_spec(repo, sample_process_spec_data):
    created = await repo.create_process_spec(sample_process_spec_data)
    result = await repo.delete_process_spec(created.id)
    assert result is True
