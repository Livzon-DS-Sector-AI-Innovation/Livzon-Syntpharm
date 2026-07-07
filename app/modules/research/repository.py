"""Research database queries."""

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.models import (
    PilotWorkflow,
    PilotWorkflowStep,
    RdStageDeliverable,
    ResearchProject,
)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


async def exists_by_project_no(
    db: AsyncSession,
    project_no: str,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    query = select(ResearchProject.id).where(
        ResearchProject.project_no == project_no,
        ResearchProject.is_deleted == False,  # noqa: E712
    )
    if exclude_id:
        query = query.where(ResearchProject.id != exclude_id)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def create_project(db: AsyncSession, data: dict[str, Any]) -> ResearchProject:
    project = ResearchProject(**data)
    db.add(project)
    await db.flush()
    return project


async def get_project_by_id(
    db: AsyncSession, project_id: uuid.UUID
) -> ResearchProject | None:
    result = await db.execute(
        select(ResearchProject).where(
            ResearchProject.id == project_id,
            ResearchProject.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_projects(
    db: AsyncSession,
    stage: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    project_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ResearchProject], int]:
    query = select(ResearchProject).where(
        ResearchProject.is_deleted == False,  # noqa: E712
    )
    count_query = (
        select(func.count())
        .select_from(ResearchProject)
        .where(
            ResearchProject.is_deleted == False,  # noqa: E712
        )
    )

    if stage:
        query = query.where(ResearchProject.stage == stage)
        count_query = count_query.where(ResearchProject.stage == stage)
    if status:
        query = query.where(ResearchProject.status == status)
        count_query = count_query.where(ResearchProject.status == status)
    if keyword:
        pattern = f"%{_escape_like(keyword)}%"
        like_filter = or_(
            ResearchProject.project_no.ilike(pattern),
            ResearchProject.name.ilike(pattern),
        )
        query = query.where(like_filter)
        count_query = count_query.where(like_filter)
    if project_type is not None:
        if project_type == "":
            query = query.where(ResearchProject.project_type is None)
            count_query = count_query.where(ResearchProject.project_type is None)
        else:
            query = query.where(ResearchProject.project_type == project_type)
            count_query = count_query.where(
                ResearchProject.project_type == project_type
            )

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(ResearchProject.updated_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def update_project(
    db: AsyncSession,
    project: ResearchProject,
    data: dict[str, Any],
) -> ResearchProject:
    for key, value in data.items():
        setattr(project, key, value)
    await db.flush()
    return project


async def delete_project(db: AsyncSession, project: ResearchProject) -> None:
    project.is_deleted = True
    await db.flush()


# ===== Pilot Workflow Repository =====


async def create_workflow(db: AsyncSession, data: dict[str, Any]) -> PilotWorkflow:
    workflow = PilotWorkflow(**data)
    db.add(workflow)
    await db.flush()
    return workflow


async def get_workflow_by_id(
    db: AsyncSession, workflow_id: uuid.UUID
) -> PilotWorkflow | None:
    result = await db.execute(
        select(PilotWorkflow).where(
            PilotWorkflow.id == workflow_id,
            PilotWorkflow.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_workflows(
    db: AsyncSession,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[PilotWorkflow], int]:
    query = select(PilotWorkflow).where(
        PilotWorkflow.is_deleted == False,  # noqa: E712
    )
    count_query = (
        select(func.count())
        .select_from(PilotWorkflow)
        .where(
            PilotWorkflow.is_deleted == False,  # noqa: E712
        )
    )

    if status:
        query = query.where(PilotWorkflow.status == status)
        count_query = count_query.where(PilotWorkflow.status == status)
    if keyword:
        pattern = f"%{_escape_like(keyword)}%"
        query = query.where(PilotWorkflow.product_name.ilike(pattern))
        count_query = count_query.where(PilotWorkflow.product_name.ilike(pattern))

    total = (await db.execute(count_query)).scalar_one()

    query = (
        query.order_by(PilotWorkflow.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return result.scalars().all(), total


async def delete_workflow(db: AsyncSession, workflow: PilotWorkflow) -> None:
    workflow.is_deleted = True
    await db.flush()


async def get_workflow_steps(
    db: AsyncSession, workflow_id: uuid.UUID
) -> list[PilotWorkflowStep]:
    result = await db.execute(
        select(PilotWorkflowStep)
        .where(
            PilotWorkflowStep.workflow_id == workflow_id,
            PilotWorkflowStep.is_deleted == False,  # noqa: E712
        )
        .order_by(PilotWorkflowStep.step_order)
    )
    return list(result.scalars().all())


async def get_workflow_step_by_id(
    db: AsyncSession, step_id: uuid.UUID
) -> PilotWorkflowStep | None:
    result = await db.execute(
        select(PilotWorkflowStep).where(
            PilotWorkflowStep.id == step_id,
            PilotWorkflowStep.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


# ===== RdProject Repository Functions =====

from app.modules.research.models import (
    RdMilestone,
    RdProject,
    RdResearchFinding,
    RdResearchTrack,
    RdStageRecord,
)


async def get_rd_projects(
    db: AsyncSession,
    stage: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    project_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RdProject], int]:
    """获取 RdProject 列表"""
    query = select(RdProject).where(~RdProject.is_deleted)

    if stage:
        query = query.where(RdProject.current_stage == stage)
    if status:
        query = query.where(RdProject.status == status)
    if keyword:
        query = query.where(
            or_(
                RdProject.name.ilike(f"%{keyword}%"),
                RdProject.api_name.ilike(f"%{keyword}%"),
                RdProject.cas_number.ilike(f"%{keyword}%"),
            )
        )
    if project_type:
        query = query.where(RdProject.project_type == project_type)

    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # 分页
    query = query.order_by(RdProject.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    projects = list(result.scalars().all())

    return projects, total


async def get_rd_project_by_id(
    db: AsyncSession, project_id: uuid.UUID
) -> RdProject | None:
    """根据 ID 获取 RdProject"""
    result = await db.execute(
        select(RdProject).where(
            RdProject.id == project_id,
            not RdProject.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_rd_project(db: AsyncSession, data: dict[str, Any]) -> RdProject:
    """创建 RdProject"""
    project = RdProject(**data)
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def update_rd_project(
    db: AsyncSession, project: RdProject, data: dict[str, Any]
) -> RdProject:
    """更新 RdProject"""
    for key, value in data.items():
        if value is not None:
            setattr(project, key, value)
    await db.flush()
    await db.refresh(project)
    return project


async def delete_rd_project(db: AsyncSession, project: RdProject) -> None:
    """删除 RdProject（软删除）"""
    project.is_deleted = True
    await db.flush()


# ===== RdMilestone Repository Functions =====


async def get_milestones_by_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[RdMilestone]:
    """获取项目的所有里程碑"""
    result = await db.execute(
        select(RdMilestone)
        .where(
            RdMilestone.project_id == project_id,
            not RdMilestone.is_deleted,
        )
        .order_by(RdMilestone.planned_date.asc())
    )
    return list(result.scalars().all())


async def get_milestone_by_id(
    db: AsyncSession, milestone_id: uuid.UUID
) -> RdMilestone | None:
    """根据 ID 获取里程碑"""
    result = await db.execute(
        select(RdMilestone).where(
            RdMilestone.id == milestone_id,
            not RdMilestone.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_milestone(db: AsyncSession, data: dict[str, Any]) -> RdMilestone:
    """创建里程碑"""
    milestone = RdMilestone(**data)
    db.add(milestone)
    await db.flush()
    await db.refresh(milestone)
    return milestone


async def update_milestone(
    db: AsyncSession, milestone: RdMilestone, data: dict[str, Any]
) -> RdMilestone:
    """更新里程碑"""
    for key, value in data.items():
        if value is not None:
            setattr(milestone, key, value)
    await db.flush()
    await db.refresh(milestone)
    return milestone


# ===== RdStageRecord Repository Functions =====


async def get_stages_by_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[RdStageRecord]:
    """获取项目的所有阶段记录"""
    result = await db.execute(
        select(RdStageRecord)
        .where(
            RdStageRecord.project_id == project_id,
            not RdStageRecord.is_deleted,
        )
        .order_by(RdStageRecord.version.desc())
    )
    return list(result.scalars().all())


async def get_stage_by_id(
    db: AsyncSession, record_id: uuid.UUID
) -> RdStageRecord | None:
    """根据 ID 获取阶段记录"""
    result = await db.execute(
        select(RdStageRecord).where(
            RdStageRecord.id == record_id,
            not RdStageRecord.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_stage_record(db: AsyncSession, data: dict[str, Any]) -> RdStageRecord:
    """创建阶段记录"""
    record = RdStageRecord(**data)
    db.add(record)
    await db.flush()
    await db.refresh(record)
    return record


async def update_stage_record(
    db: AsyncSession, record: RdStageRecord, data: dict[str, Any]
) -> RdStageRecord:
    """更新阶段记录"""
    for key, value in data.items():
        if value is not None:
            setattr(record, key, value)
    await db.flush()
    await db.refresh(record)
    return record


# ===== RdResearchTrack Repository Functions =====


async def get_tracks_by_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[RdResearchTrack]:
    """获取项目的所有研究项"""
    result = await db.execute(
        select(RdResearchTrack)
        .where(
            RdResearchTrack.project_id == project_id,
            not RdResearchTrack.is_deleted,
        )
        .order_by(RdResearchTrack.created_at.desc())
    )
    return list(result.scalars().all())


async def get_track_by_id(
    db: AsyncSession, track_id: uuid.UUID
) -> RdResearchTrack | None:
    """根据 ID 获取研究项"""
    result = await db.execute(
        select(RdResearchTrack).where(
            RdResearchTrack.id == track_id,
            not RdResearchTrack.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_research_track(
    db: AsyncSession, data: dict[str, Any]
) -> RdResearchTrack:
    """创建研究项"""
    track = RdResearchTrack(**data)
    db.add(track)
    await db.flush()
    await db.refresh(track)
    return track


async def update_research_track(
    db: AsyncSession, track: RdResearchTrack, data: dict[str, Any]
) -> RdResearchTrack:
    """更新研究项"""
    for key, value in data.items():
        if value is not None:
            setattr(track, key, value)
    await db.flush()
    await db.refresh(track)
    return track


# ===== RdResearchFinding Repository Functions =====


async def get_findings_by_track(
    db: AsyncSession, track_id: uuid.UUID
) -> list[RdResearchFinding]:
    """获取研究项的所有发现"""
    result = await db.execute(
        select(RdResearchFinding)
        .where(
            RdResearchFinding.track_id == track_id,
            not RdResearchFinding.is_deleted,
        )
        .order_by(RdResearchFinding.version.desc())
    )
    return list(result.scalars().all())


async def get_finding_by_id(
    db: AsyncSession, finding_id: uuid.UUID
) -> RdResearchFinding | None:
    """根据 ID 获取研究发现"""
    result = await db.execute(
        select(RdResearchFinding).where(
            RdResearchFinding.id == finding_id,
            not RdResearchFinding.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_research_finding(
    db: AsyncSession, data: dict[str, Any]
) -> RdResearchFinding:
    """创建研究发现"""
    finding = RdResearchFinding(**data)
    db.add(finding)
    await db.flush()
    await db.refresh(finding)
    return finding


async def update_research_finding(
    db: AsyncSession, finding: RdResearchFinding, data: dict[str, Any]
) -> RdResearchFinding:
    """更新研究发现"""
    for key, value in data.items():
        if value is not None:
            setattr(finding, key, value)
    await db.flush()
    await db.refresh(finding)
    return finding


# ===== RdPilotStudy Repository Functions =====

from app.modules.research.models import (
    RdPilotStudy,
    RdProcessValidation,
    RdRegistrationFiling,
)


async def get_pilot_studies_by_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[RdPilotStudy]:
    """获取项目的所有中试研究记录"""
    result = await db.execute(
        select(RdPilotStudy)
        .where(
            RdPilotStudy.project_id == project_id,
            not RdPilotStudy.is_deleted,
        )
        .order_by(RdPilotStudy.created_at.desc())
    )
    return list(result.scalars().all())


async def get_pilot_study_by_id(
    db: AsyncSession, study_id: uuid.UUID
) -> RdPilotStudy | None:
    """根据 ID 获取中试研究记录"""
    result = await db.execute(
        select(RdPilotStudy).where(
            RdPilotStudy.id == study_id,
            not RdPilotStudy.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_pilot_study(db: AsyncSession, data: dict[str, Any]) -> RdPilotStudy:
    """创建中试研究记录"""
    study = RdPilotStudy(**data)
    db.add(study)
    await db.flush()
    await db.refresh(study)
    return study


async def update_pilot_study(
    db: AsyncSession, study: RdPilotStudy, data: dict[str, Any]
) -> RdPilotStudy:
    """更新中试研究记录"""
    for key, value in data.items():
        if value is not None:
            setattr(study, key, value)
    await db.flush()
    await db.refresh(study)
    return study


# ===== RdProcessValidation Repository Functions =====


async def get_validations_by_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[RdProcessValidation]:
    """获取项目的所有工艺验证记录"""
    result = await db.execute(
        select(RdProcessValidation)
        .where(
            RdProcessValidation.project_id == project_id,
            not RdProcessValidation.is_deleted,
        )
        .order_by(RdProcessValidation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_validation_by_id(
    db: AsyncSession, validation_id: uuid.UUID
) -> RdProcessValidation | None:
    """根据 ID 获取工艺验证记录"""
    result = await db.execute(
        select(RdProcessValidation).where(
            RdProcessValidation.id == validation_id,
            not RdProcessValidation.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_validation(
    db: AsyncSession, data: dict[str, Any]
) -> RdProcessValidation:
    """创建工艺验证记录"""
    validation = RdProcessValidation(**data)
    db.add(validation)
    await db.flush()
    await db.refresh(validation)
    return validation


async def update_validation(
    db: AsyncSession, validation: RdProcessValidation, data: dict[str, Any]
) -> RdProcessValidation:
    """更新工艺验证记录"""
    for key, value in data.items():
        if value is not None:
            setattr(validation, key, value)
    await db.flush()
    await db.refresh(validation)
    return validation


# ===== RdRegistrationFiling Repository Functions =====


async def get_filings_by_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list[RdRegistrationFiling]:
    """获取项目的所有申报资料记录"""
    result = await db.execute(
        select(RdRegistrationFiling)
        .where(
            RdRegistrationFiling.project_id == project_id,
            not RdRegistrationFiling.is_deleted,
        )
        .order_by(RdRegistrationFiling.created_at.desc())
    )
    return list(result.scalars().all())


async def get_filing_by_id(
    db: AsyncSession, filing_id: uuid.UUID
) -> RdRegistrationFiling | None:
    """根据 ID 获取申报资料记录"""
    result = await db.execute(
        select(RdRegistrationFiling).where(
            RdRegistrationFiling.id == filing_id,
            not RdRegistrationFiling.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_filing(db: AsyncSession, data: dict[str, Any]) -> RdRegistrationFiling:
    """创建申报资料记录"""
    filing = RdRegistrationFiling(**data)
    db.add(filing)
    await db.flush()
    await db.refresh(filing)
    return filing


async def update_filing(
    db: AsyncSession, filing: RdRegistrationFiling, data: dict[str, Any]
) -> RdRegistrationFiling:
    """更新申报资料记录"""
    for key, value in data.items():
        if value is not None:
            setattr(filing, key, value)
    await db.flush()
    await db.refresh(filing)
    return filing


# ===== RdStageDeliverable Repository =====


async def create_rd_stage_deliverable(
    db: AsyncSession, data: dict
) -> RdStageDeliverable:
    """创建阶段交付物"""
    deliverable = RdStageDeliverable(**data)
    db.add(deliverable)
    await db.commit()
    await db.refresh(deliverable)
    return deliverable


async def get_rd_stage_deliverable(
    db: AsyncSession, deliverable_id: uuid.UUID
) -> RdStageDeliverable:
    """获取阶段交付物"""
    result = await db.execute(
        select(RdStageDeliverable).where(RdStageDeliverable.id == deliverable_id)
    )
    deliverable = result.scalar_one_or_none()
    if not deliverable:
        raise HTTPException(status_code=404, detail="交付物不存在")
    return deliverable


async def list_rd_stage_deliverables(
    db: AsyncSession,
    project_id: uuid.UUID | None = None,
    stage: str | None = None,
    deliverable_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RdStageDeliverable], int]:
    """获取阶段交付物列表"""
    query = select(RdStageDeliverable)
    count_query = select(func.count(RdStageDeliverable.id))

    if project_id:
        query = query.where(RdStageDeliverable.project_id == project_id)
        count_query = count_query.where(RdStageDeliverable.project_id == project_id)
    if stage:
        query = query.where(RdStageDeliverable.stage == stage)
        count_query = count_query.where(RdStageDeliverable.stage == stage)
    if deliverable_type:
        query = query.where(RdStageDeliverable.deliverable_type == deliverable_type)
        count_query = count_query.where(
            RdStageDeliverable.deliverable_type == deliverable_type
        )
    if status:
        query = query.where(RdStageDeliverable.status == status)
        count_query = count_query.where(RdStageDeliverable.status == status)

    # 获取总数
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(desc(RdStageDeliverable.created_at))
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def update_rd_stage_deliverable(
    db: AsyncSession, deliverable: RdStageDeliverable, data: dict
) -> RdStageDeliverable:
    """更新阶段交付物"""
    for key, value in data.items():
        setattr(deliverable, key, value)
    await db.commit()
    await db.refresh(deliverable)
    return deliverable


async def delete_rd_stage_deliverable(
    db: AsyncSession, deliverable: RdStageDeliverable
) -> None:
    """删除阶段交付物"""
    await db.delete(deliverable)
    await db.commit()


async def delete_pilot_study(
    db: AsyncSession, study_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """软删除中试研究"""
    result = await db.execute(select(RdPilotStudy).where(RdPilotStudy.id == study_id))
    study = result.scalar_one_or_none()
    if not study:
        raise HTTPException(status_code=404, detail="中试研究不存在")
    study.is_deleted = True
    if user_id:
        study.updated_by = user_id
    await db.flush()


async def delete_validation(
    db: AsyncSession, validation_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """软删除工艺验证"""
    result = await db.execute(
        select(RdProcessValidation).where(RdProcessValidation.id == validation_id)
    )
    validation = result.scalar_one_or_none()
    if not validation:
        raise HTTPException(status_code=404, detail="工艺验证不存在")
    validation.is_deleted = True
    if user_id:
        validation.updated_by = user_id
    await db.flush()


async def delete_filing(
    db: AsyncSession, filing_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """软删除申报资料"""
    result = await db.execute(
        select(RdRegistrationFiling).where(RdRegistrationFiling.id == filing_id)
    )
    filing = result.scalar_one_or_none()
    if not filing:
        raise HTTPException(status_code=404, detail="申报资料不存在")
    filing.is_deleted = True
    if user_id:
        filing.updated_by = user_id
    await db.flush()


# ===== RdExperimentLog Repository Functions =====


async def get_experiment_logs_by_project(
    db: AsyncSession, project_id: uuid.UUID
) -> list:
    """获取项目的所有实验记录"""
    from app.modules.research.models import RdExperimentLog

    result = await db.execute(
        select(RdExperimentLog)
        .where(
            RdExperimentLog.project_id == project_id,
            not RdExperimentLog.is_deleted,
        )
        .order_by(RdExperimentLog.created_at.desc())
    )
    return list(result.scalars().all())


async def get_experiment_log_by_id(db: AsyncSession, log_id: uuid.UUID):
    """根据 ID 获取实验记录"""
    from app.modules.research.models import RdExperimentLog

    result = await db.execute(
        select(RdExperimentLog).where(
            RdExperimentLog.id == log_id,
            not RdExperimentLog.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_experiment_log(db: AsyncSession, data: dict[str, Any]):
    """创建实验记录"""
    from app.modules.research.models import RdExperimentLog

    log = RdExperimentLog(**data)
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def update_experiment_log(db: AsyncSession, log, data: dict[str, Any]):
    """更新实验记录"""
    for key, value in data.items():
        if value is not None:
            setattr(log, key, value)
    await db.flush()
    await db.refresh(log)
    return log


async def delete_experiment_log(
    db: AsyncSession, log_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除实验记录"""
    from app.modules.research.models import RdExperimentLog

    result = await db.execute(
        select(RdExperimentLog).where(
            RdExperimentLog.id == log_id,
            not RdExperimentLog.is_deleted,
        )
    )
    log = result.scalar_one_or_none()
    if log:
        log.is_deleted = True
        if user_id:
            log.updated_by = user_id
        await db.flush()


# ===== RdReport Repository Functions =====


async def get_reports_by_project(db: AsyncSession, project_id: uuid.UUID) -> list:
    """获取项目的所有研发报告"""
    from app.modules.research.models import RdReport

    result = await db.execute(
        select(RdReport)
        .where(
            RdReport.project_id == project_id,
            not RdReport.is_deleted,
        )
        .order_by(RdReport.created_at.desc())
    )
    return list(result.scalars().all())


async def get_report_by_id(db: AsyncSession, report_id: uuid.UUID):
    """根据 ID 获取研发报告"""
    from app.modules.research.models import RdReport

    result = await db.execute(
        select(RdReport).where(
            RdReport.id == report_id,
            not RdReport.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_report(db: AsyncSession, data: dict[str, Any]):
    """创建研发报告"""
    from app.modules.research.models import RdReport

    report = RdReport(**data)
    db.add(report)
    await db.flush()
    await db.refresh(report)
    return report


async def update_report(db: AsyncSession, report, data: dict[str, Any]):
    """更新研发报告"""
    for key, value in data.items():
        if value is not None:
            setattr(report, key, value)
    await db.flush()
    await db.refresh(report)
    return report


async def delete_report(
    db: AsyncSession, report_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除研发报告"""
    from app.modules.research.models import RdReport

    result = await db.execute(
        select(RdReport).where(
            RdReport.id == report_id,
            not RdReport.is_deleted,
        )
    )
    report = result.scalar_one_or_none()
    if report:
        report.is_deleted = True
        if user_id:
            report.updated_by = user_id
        await db.flush()


# ===== RdInitiation Repository Functions =====


async def get_initiations_by_project(db: AsyncSession, project_id: uuid.UUID) -> list:
    """获取项目的所有立项申请"""
    from app.modules.research.models import RdInitiation

    result = await db.execute(
        select(RdInitiation)
        .where(
            RdInitiation.project_id == project_id,
            not RdInitiation.is_deleted,
        )
        .order_by(RdInitiation.created_at.desc())
    )
    return list(result.scalars().all())


async def get_initiation_by_id(db: AsyncSession, initiation_id: uuid.UUID):
    """根据 ID 获取立项申请"""
    from app.modules.research.models import RdInitiation

    result = await db.execute(
        select(RdInitiation).where(
            RdInitiation.id == initiation_id,
            not RdInitiation.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_initiation(db: AsyncSession, data: dict[str, Any]):
    """创建立项申请"""
    from app.modules.research.models import RdInitiation

    initiation = RdInitiation(**data)
    db.add(initiation)
    await db.flush()
    await db.refresh(initiation)
    return initiation


async def update_initiation(db: AsyncSession, initiation, data: dict[str, Any]):
    """更新立项申请"""
    for key, value in data.items():
        if value is not None:
            setattr(initiation, key, value)
    await db.flush()
    await db.refresh(initiation)
    return initiation


async def delete_initiation(
    db: AsyncSession, initiation_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除立项申请"""
    from app.modules.research.models import RdInitiation

    result = await db.execute(
        select(RdInitiation).where(
            RdInitiation.id == initiation_id,
            not RdInitiation.is_deleted,
        )
    )
    initiation = result.scalar_one_or_none()
    if initiation:
        initiation.is_deleted = True
        if user_id:
            initiation.updated_by = user_id
        await db.flush()


# ===== RdTrackConclusionVersion Repository Functions =====


async def get_conclusion_versions(db: AsyncSession, track_id: uuid.UUID) -> list:
    """获取研究项的结论版本历史"""
    from app.modules.research.models import RdTrackConclusionVersion

    result = await db.execute(
        select(RdTrackConclusionVersion)
        .where(
            RdTrackConclusionVersion.track_id == track_id,
            not RdTrackConclusionVersion.is_deleted,
        )
        .order_by(RdTrackConclusionVersion.version.desc())
    )
    return list(result.scalars().all())


async def create_conclusion_version(db: AsyncSession, data: dict[str, Any]):
    """创建结论版本"""
    from app.modules.research.models import RdTrackConclusionVersion

    version = RdTrackConclusionVersion(**data)
    db.add(version)
    await db.flush()
    await db.refresh(version)
    return version


async def get_latest_conclusion_version(db: AsyncSession, track_id: uuid.UUID):
    """获取最新结论版本"""
    from app.modules.research.models import RdTrackConclusionVersion

    result = await db.execute(
        select(RdTrackConclusionVersion)
        .where(
            RdTrackConclusionVersion.track_id == track_id,
            not RdTrackConclusionVersion.is_deleted,
        )
        .order_by(RdTrackConclusionVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


# ===== RdDeliverableTemplate Repository Functions =====


async def get_deliverable_templates(
    db: AsyncSession,
    stage: str | None = None,
    deliverable_type: str | None = None,
    is_active: bool | None = None,
) -> list:
    """获取交付物模板列表"""
    from app.modules.research.models import RdDeliverableTemplate

    query = select(RdDeliverableTemplate).where(
        not RdDeliverableTemplate.is_deleted,
    )
    if stage:
        query = query.where(RdDeliverableTemplate.stage == stage)
    if deliverable_type:
        query = query.where(RdDeliverableTemplate.deliverable_type == deliverable_type)
    if is_active is not None:
        query = query.where(RdDeliverableTemplate.is_active == is_active)
    query = query.order_by(RdDeliverableTemplate.created_at.desc())
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_deliverable_template_by_id(db: AsyncSession, template_id: uuid.UUID):
    """根据 ID 获取交付物模板"""
    from app.modules.research.models import RdDeliverableTemplate

    result = await db.execute(
        select(RdDeliverableTemplate).where(
            RdDeliverableTemplate.id == template_id,
            not RdDeliverableTemplate.is_deleted,
        )
    )
    return result.scalar_one_or_none()


async def create_deliverable_template(db: AsyncSession, data: dict[str, Any]):
    """创建交付物模板"""
    from app.modules.research.models import RdDeliverableTemplate

    template = RdDeliverableTemplate(**data)
    db.add(template)
    await db.flush()
    await db.refresh(template)
    return template


async def update_deliverable_template(db: AsyncSession, template, data: dict[str, Any]):
    """更新交付物模板"""
    for key, value in data.items():
        if value is not None:
            setattr(template, key, value)
    await db.flush()
    await db.refresh(template)
    return template


async def delete_deliverable_template(
    db: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除交付物模板"""
    from app.modules.research.models import RdDeliverableTemplate

    result = await db.execute(
        select(RdDeliverableTemplate).where(
            RdDeliverableTemplate.id == template_id,
            not RdDeliverableTemplate.is_deleted,
        )
    )
    template = result.scalar_one_or_none()
    if template:
        template.is_deleted = True
        if user_id:
            template.updated_by = user_id
        await db.flush()
