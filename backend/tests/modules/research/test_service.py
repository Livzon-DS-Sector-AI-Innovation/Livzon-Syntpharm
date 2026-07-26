# mypy: ignore-errors
from __future__ import annotations

import uuid

import pytest

from app.modules.research import service
from app.modules.research.schemas import (
    RdProjectCreate,
    RdStageDeliverableCreate,
    RdPilotStudyCreate,
    RdExperimentLogCreate,
)


# ============ RdProject ============


@pytest.mark.asyncio
async def test_create_and_get_rd_project(db_session):
    proj = await service.create_rd_project(
        db_session,
        RdProjectCreate(
            name=f"测试研发项目-{uuid.uuid4().hex[:6]}",
            api_name="阿莫西林",
        ),
    )
    assert proj.id is not None
    fetched = await service.get_rd_project(db_session, proj.id)
    assert fetched.name == proj.name


@pytest.mark.asyncio
async def test_get_rd_project_not_found(db_session):
    from app.core.exceptions import NotFoundException

    with pytest.raises(NotFoundException):
        await service.get_rd_project(db_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_delete_rd_project(db_session):
    from app.core.exceptions import NotFoundException

    proj = await service.create_rd_project(
        db_session,
        RdProjectCreate(
            name=f"待删除项目-{uuid.uuid4().hex[:6]}",
            api_name="头孢",
        ),
    )
    await service.delete_rd_project(db_session, proj.id)
    with pytest.raises(NotFoundException):
        await service.get_rd_project(db_session, proj.id)


# ============ RdStageDeliverable ============


@pytest.mark.asyncio
async def test_create_deliverable(db_session):
    proj = await service.create_rd_project(
        db_session,
        RdProjectCreate(
            name=f"测试项目-{uuid.uuid4().hex[:6]}",
            api_name="阿莫西林",
        ),
    )
    deliverable = await service.create_rd_stage_deliverable(
        db_session,
        RdStageDeliverableCreate(
            project_id=proj.id,
            stage="development",
            deliverable_type="report",
            title="工艺开发报告",
        ),
    )
    assert deliverable.title == "工艺开发报告"


@pytest.mark.asyncio
async def test_get_deliverable(db_session):
    proj = await service.create_rd_project(
        db_session,
        RdProjectCreate(
            name=f"测试项目-{uuid.uuid4().hex[:6]}",
            api_name="阿莫西林",
        ),
    )
    d = await service.create_rd_stage_deliverable(
        db_session,
        RdStageDeliverableCreate(
            project_id=proj.id,
            stage="development",
            deliverable_type="report",
            title="工艺开发报告",
        ),
    )
    fetched = await service.get_rd_stage_deliverable(db_session, d.id)
    assert fetched is not None


# ============ RdPilotStudy ============


@pytest.mark.asyncio
async def test_create_pilot_study(db_session):
    proj = await service.create_rd_project(
        db_session,
        RdProjectCreate(
            name=f"测试项目-{uuid.uuid4().hex[:6]}",
            api_name="阿莫西林",
        ),
    )
    study = await service.create_pilot_study(
        db_session,
        RdPilotStudyCreate(
            project_id=proj.id,
            batch_no="PILOT-001",
        ),
    )
    assert study.batch_no == "PILOT-001"


# ============ RdExperimentLog ============


@pytest.mark.asyncio
async def test_create_experiment_log(db_session):
    proj = await service.create_rd_project(
        db_session,
        RdProjectCreate(
            name=f"测试项目-{uuid.uuid4().hex[:6]}",
            api_name="阿莫西林",
        ),
    )
    log = await service.create_experiment_log(
        db_session,
        RdExperimentLogCreate(
            project_id=proj.id,
            title="结晶条件优化实验",
            experiment_type="optimization",
        ),
    )
    assert log.title == "结晶条件优化实验"
