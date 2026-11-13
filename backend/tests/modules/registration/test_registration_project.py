# mypy: ignore-errors
"""注册项目页改版：状态机 / 阶段推进 / 进展留痕 / KPI / 申报进度同步 集成测试。"""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.models.drug import Drug, DrugNode
from app.modules.registration.schemas.project import ProjectCreate
from app.modules.registration.service import project as project_service
from app.modules.registration.service.project import sync_from_drug


def _create_payload(**overrides) -> ProjectCreate:
    data = {
        "name": f"测试项目-{uuid.uuid4().hex[:6]}",
        "product_name": "测试品种",
        "registration_type": "新注册",
        "owner": "测试负责人",
    }
    data.update(overrides)
    return ProjectCreate(**data)


async def test_create_project_writes_creation_log(db_session: AsyncSession):
    """创建项目：状态=草稿、阶段=立项、自动生成编号、自动写入创建 system 记录。"""
    project = await project_service.create_project(db_session, _create_payload())

    assert project.status == "draft"
    assert project.pre_stage == "initiation"
    assert project.project_no and project.project_no.startswith("REG-")
    assert "initiation" in project.stage_completed_at

    logs = await project_service.get_project_logs(db_session, project.id)
    assert len(logs) == 1
    assert logs[0]["log_type"] == "system"
    assert logs[0]["content"] == "项目创建，初始状态：草稿"


async def test_advance_stage_flows_status_and_logs(db_session: AsyncSession):
    """推进阶段：状态随阶段自动流转，状态变更写 system 记录（格式：草稿 → 准备中）。"""
    project = await project_service.create_project(db_session, _create_payload())

    project = await project_service.advance_stage(db_session, project.id, "data_preparation")
    assert project.status == "preparing"
    assert project.pre_stage == "data_preparation"

    logs = await project_service.get_project_logs(db_session, project.id)
    contents = [log["content"] for log in logs]
    assert "草稿 → 准备中" in contents

    # 资料准备 → 内部审核：状态不变（均为准备中），记录阶段推进
    project = await project_service.advance_stage(db_session, project.id, "internal_review")
    assert project.status == "preparing"
    contents = [log["content"] for log in await project_service.get_project_logs(db_session, project.id)]
    assert "阶段推进：资料准备 → 内部审核" in contents

    # 推进到递交：状态 → 已申报，自动记录申报日期
    project = await project_service.advance_stage(db_session, project.id, "submission")
    assert project.status == "submitted"
    assert project.submitted_at is not None
    contents = [log["content"] for log in await project_service.get_project_logs(db_session, project.id)]
    assert "准备中 → 已申报" in contents


async def test_advance_to_accepted_stage_rejected(db_session: AsyncSession):
    """「已受理」阶段不可手动点达，只能由申报进度查询侧同步。"""
    project = await project_service.create_project(db_session, _create_payload())
    with pytest.raises(ValueError, match="已受理"):
        await project_service.advance_stage(db_session, project.id, "accepted")


async def test_update_project_cannot_change_status(db_session: AsyncSession):
    """更新接口不接受状态/阶段字段（本页无修改状态入口）。"""
    from app.modules.registration.schemas.project import ProjectUpdate

    assert "status" not in ProjectUpdate.model_fields
    assert "pre_stage" not in ProjectUpdate.model_fields


async def test_manual_log_append_only_with_creator(db_session: AsyncSession):
    """手动进展记录：自动带时间与登录人；时间线新→旧倒序。"""
    project = await project_service.create_project(db_session, _create_payload())
    log = await project_service.add_progress_log(db_session, project.id, "3.2.S 初稿完成")

    assert log["log_type"] == "manual"
    assert log["content"] == "3.2.S 初稿完成"

    logs = await project_service.get_project_logs(db_session, project.id)
    assert logs[0]["content"] == "3.2.S 初稿完成"  # 最新在前
    assert logs[-1]["content"] == "项目创建，初始状态：草稿"

    # 最新进展冗余字段同步更新
    project = await project_service.get_project(db_session, project.id)
    assert project.latest_progress == "3.2.S 初稿完成"


async def test_kpi_counts(db_session: AsyncSession):
    """KPI：申报前 / 已受理·审评中 / 临期未递交 / 已获批 计数正确。"""
    baseline = await project_service.get_kpi(db_session)

    await project_service.create_project(
        db_session, _create_payload(planned_submission_date=date.today() + timedelta(days=10))
    )
    await project_service.create_project(
        db_session, _create_payload(planned_submission_date=date.today() + timedelta(days=90))
    )

    kpi = await project_service.get_kpi(db_session)
    assert kpi["pre_submission"] - baseline["pre_submission"] == 2
    assert kpi["due_soon"] - baseline["due_soon"] == 1  # 只有 10 天后的计入


async def test_sync_from_drug_acceptance_then_progress(db_session: AsyncSession):
    """申报进度查询侧登记受理号 → 项目自动置「已受理」；节点推进 → 审评中 → 已获批。"""
    drug = Drug(name=f"测试药品-{uuid.uuid4().hex[:6]}", type="原料药", acceptance_date=date(2026, 11, 1))
    db_session.add(drug)
    await db_session.flush()

    project = await project_service.create_project(db_session, _create_payload(drug_id=drug.id))
    await project_service.advance_stage(db_session, project.id, "submission")

    # 1) 登记受理号 → 已受理 + 阶段置达 + system 记录
    drug.acceptance_number = "CXHS2600001"
    await sync_from_drug(db_session, drug.id)
    await db_session.refresh(project)
    assert project.status == "accepted"
    assert project.pre_stage == "accepted"
    assert project.acceptance_number == "CXHS2600001"
    assert project.accepted_at == date(2026, 11, 1)
    contents = [log["content"] for log in await project_service.get_project_logs(db_session, project.id)]
    assert "已申报 → 已受理" in contents

    # 已受理后不再允许手动推进阶段
    with pytest.raises(ValueError, match="只读"):
        await project_service.advance_stage(db_session, project.id, "initiation")

    # 2) 推进一个普通审评节点 → 审评中
    db_session.add(DrugNode(drug_id=drug.id, node_index=1, actual_date=date(2026, 11, 5)))
    await db_session.flush()
    await sync_from_drug(db_session, drug.id)
    await db_session.refresh(project)
    assert project.status == "under_review"
    contents = [log["content"] for log in await project_service.get_project_logs(db_session, project.id)]
    assert "已受理 → 审评中" in contents

    # 3) 发补节点完成 → 发补中
    db_session.add(DrugNode(drug_id=drug.id, node_index=7, actual_date=date(2026, 11, 8)))
    await db_session.flush()
    await sync_from_drug(db_session, drug.id)
    await db_session.refresh(project)
    assert project.status == "supplementary"

    # 4) 全部节点完成 → 已获批（节点 1、7 已在前面步骤创建）
    for idx in (2, 3, 4, 5, 6, 8, 9, 10):
        db_session.add(DrugNode(drug_id=drug.id, node_index=idx, actual_date=date(2026, 11, 9)))
    await db_session.flush()
    await sync_from_drug(db_session, drug.id)
    await db_session.refresh(project)
    assert project.status == "approved"
    assert project.approved_at is not None
    contents = [log["content"] for log in await project_service.get_project_logs(db_session, project.id)]
    assert "发补中 → 已获批" in contents


async def test_project_api_flow(auth_client: AsyncClient):
    """API 契约：创建 → 列表筛选 → KPI → 阶段推进 → 进展记录。"""
    create_resp = await auth_client.post(
        "/api/v1/registration/projects/",
        json={
            "name": "API 测试项目",
            "product_name": "API 品种",
            "registration_type": "变更",
            "owner": "测试人",
        },
    )
    assert create_resp.status_code == 200, create_resp.text
    project = create_resp.json()["data"]
    assert project["status"] == "draft"
    assert project["pre_stage"] == "initiation"

    list_resp = await auth_client.get("/api/v1/registration/projects/", params={"search": "API 测试项目"})
    assert list_resp.status_code == 200
    assert any(p["id"] == project["id"] for p in list_resp.json()["data"])

    kpi_resp = await auth_client.get("/api/v1/registration/projects/kpi")
    assert kpi_resp.status_code == 200
    assert set(kpi_resp.json()["data"]) == {"pre_submission", "accepted_reviewing", "due_soon", "approved"}

    stage_resp = await auth_client.post(
        f"/api/v1/registration/projects/{project['id']}/stage", json={"stage": "data_preparation"}
    )
    assert stage_resp.status_code == 200
    assert stage_resp.json()["data"]["status"] == "preparing"

    log_resp = await auth_client.post(
        f"/api/v1/registration/projects/{project['id']}/logs", json={"content": "API 进展记录"}
    )
    assert log_resp.status_code == 200
    assert log_resp.json()["data"]["created_by_name"] == "Test User"

    logs_resp = await auth_client.get(f"/api/v1/registration/projects/{project['id']}/logs")
    assert logs_resp.status_code == 200
    assert logs_resp.json()["data"][0]["content"] == "API 进展记录"

    # 受理后状态无修改入口：stage 接口拒绝 accepted
    reject = await auth_client.post(f"/api/v1/registration/projects/{project['id']}/stage", json={"stage": "accepted"})
    assert reject.status_code == 400
