"""Research business workflows."""

import logging
import re
import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateException, NotFoundException

logger = logging.getLogger(__name__)
from app.modules.research import repository as repo  # noqa: E402
from app.modules.research.models import (  # noqa: E402
    ProcessOptimization,
    RdDeliverableTemplate,
    RdExperimentLog,
    RdMilestone,
    RdPilotStudy,
    RdProcessValidation,
    RdProject,
    RdRegistrationFiling,
    RdResearchFinding,
    RdResearchTrack,
    RdStageDeliverable,
    RdStageRecord,
    ResearchProject,
)
from app.modules.research.schemas import (  # noqa: E402
    RdMilestoneCreate,
    RdMilestoneUpdate,
    RdPilotStudyCreate,
    RdPilotStudyUpdate,
    RdProcessValidationCreate,
    RdProcessValidationUpdate,
    RdProjectCreate,
    RdProjectUpdate,
    RdRegistrationFilingCreate,
    RdRegistrationFilingUpdate,
    RdResearchFindingCreate,
    RdResearchFindingUpdate,
    RdResearchTrackCreate,
    RdResearchTrackUpdate,
    RdStageDeliverableCreate,
    RdStageDeliverableUpdate,
    RdStageRecordCreate,
    RdStageRecordUpdate,
    ResearchProjectCreate,
    ResearchProjectUpdate,
)


async def create_project(db: AsyncSession, data: ResearchProjectCreate) -> ResearchProject:
    # Auto-generate project_no if not provided
    project_no = data.project_no
    if not project_no:
        project_no = f"PRJ-{str(uuid.uuid4())[:8].upper()}"

    if await repo.exists_by_project_no(db, project_no):
        raise DuplicateException("项目编号", project_no)

    project_data = data.model_dump()
    project_data["project_no"] = project_no
    return await repo.create_project(db, project_data)


async def get_project(db: AsyncSession, project_id: uuid.UUID) -> RdProject:
    project = await repo.get_rd_project_by_id(db, project_id)
    if not project:
        raise NotFoundException("研发项目", str(project_id))
    return project


async def get_rd_project(db: AsyncSession, project_id: UUID) -> RdProject:
    """获取 RdProject（用于 rd_milestones 等外键验证）"""
    result = await db.execute(
        select(RdProject).where(
            RdProject.id == project_id,
            ~RdProject.is_deleted,
        )
    )
    project = result.scalar_one_or_none()
    if not project:
        raise NotFoundException("研发项目", str(project_id))
    return project


async def get_projects(
    db: AsyncSession,
    stage: str | None = None,
    status: str | None = None,
    keyword: str | None = None,
    project_type: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ResearchProject], int]:
    return await repo.get_projects(
        db,
        stage=stage,
        status=status,
        keyword=keyword,
        project_type=project_type,
        page=page,
        page_size=page_size,
    )


async def update_project(
    db: AsyncSession,
    project_id: uuid.UUID,
    data: ResearchProjectUpdate,
) -> ResearchProject:
    project = await get_project(db, project_id)
    update_data = data.model_dump(exclude_unset=True)
    if "project_no" in update_data and update_data["project_no"] != project.project_no:  # type: ignore[attr-defined]
        if await repo.exists_by_project_no(db, update_data["project_no"], exclude_id=project_id):
            raise DuplicateException("项目编号", update_data["project_no"])
    return await repo.update_project(db, project, update_data)  # type: ignore[arg-type]


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await get_project(db, project_id)
    await repo.delete_project(db, project)  # type: ignore[arg-type]


# ICH Analysis functions
from sqlalchemy import func, select  # noqa: E402

from app.modules.research.models import ICHAnalysisRecord  # noqa: E402


async def analyze_ich_q3c(
    db: AsyncSession,
    file_content: bytes,
    filename: str,
    route: str | None = None,
) -> dict:  # type: ignore[type-arg]
    """Analyze ICH Q3C solvent residuals from uploaded file."""
    # TODO: Implement actual Q3C analysis logic
    # For now, create a placeholder record
    record = ICHAnalysisRecord(
        filename=filename,
        route=route,
        q3c_result={"status": "pending", "message": "Q3C analysis not yet implemented"},
        q3d_result=None,
        llm_used=False,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "id": str(record.id),
        "filename": record.filename,
        "route": record.route,
        "q3c_result": record.q3c_result,
        "q3d_result": record.q3d_result,
        "llm_used": record.llm_used,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


async def analyze_ich_combined(
    db: AsyncSession,
    file_content: bytes,
    filename: str,
    route: str | None = None,
    use_llm: bool = False,
) -> dict:  # type: ignore[type-arg]
    """Analyze ICH Q3C/Q3D combined analysis from uploaded file."""
    # TODO: Implement actual combined analysis logic
    # For now, create a placeholder record
    record = ICHAnalysisRecord(
        filename=filename,
        route=route,
        q3c_result={"status": "pending", "message": "Q3C analysis not yet implemented"},
        q3d_result={"status": "pending", "message": "Q3D analysis not yet implemented"},
        llm_used=use_llm,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    return {
        "id": str(record.id),
        "filename": record.filename,
        "route": record.route,
        "q3c_result": record.q3c_result,
        "q3d_result": record.q3d_result,
        "llm_used": record.llm_used,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }


async def get_ich_records(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[ICHAnalysisRecord], int]:
    """Get paginated ICH analysis records."""
    # Get total count
    count_query = select(func.count()).select_from(ICHAnalysisRecord)
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated records
    query = (
        select(ICHAnalysisRecord)
        .order_by(ICHAnalysisRecord.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    records = list(result.scalars().all())

    return records, total


async def get_ich_record(
    db: AsyncSession,
    record_id: uuid.UUID,
) -> ICHAnalysisRecord:
    """Get single ICH analysis record by ID."""
    query = select(ICHAnalysisRecord).where(ICHAnalysisRecord.id == record_id)
    result = await db.execute(query)
    record = result.scalar_one_or_none()

    if not record:
        raise NotFoundException("ICH Q3C/Q3D 杂质识别记录", str(record_id))

    return record


async def delete_ich_record(
    db: AsyncSession,
    record_id: uuid.UUID,
) -> None:
    """Delete ICH analysis record by ID."""
    record = await get_ich_record(db, record_id)
    await db.delete(record)
    await db.commit()


# ===== Milestone Service =====


async def create_milestone(
    db: AsyncSession,
    project_id: UUID,
    data: RdMilestoneCreate,
    user_id: UUID | None = None,
) -> RdMilestone:
    """创建里程碑"""
    await get_rd_project(db, project_id)  # 验证项目存在
    milestone = RdMilestone(
        project_id=project_id,
        **data.model_dump(),
        status="planned",
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(milestone)
    await db.commit()
    await db.refresh(milestone)
    return milestone


async def get_milestones(db: AsyncSession, project_id: UUID) -> list[RdMilestone]:
    """获取项目的里程碑列表"""
    result = await db.execute(
        select(RdMilestone)
        .where(RdMilestone.project_id == project_id, ~RdMilestone.is_deleted)
        .order_by(RdMilestone.planned_date)
    )
    return list(result.scalars().all())


async def update_milestone(
    db: AsyncSession,
    milestone_id: UUID,
    data: RdMilestoneUpdate,
    user_id: UUID | None = None,
) -> RdMilestone:
    """更新里程碑"""
    result = await db.execute(
        select(RdMilestone).where(
            RdMilestone.id == milestone_id,
            ~RdMilestone.is_deleted,
        )
    )
    milestone = result.scalar_one_or_none()
    if not milestone:
        raise HTTPException(status_code=404, detail="里程碑不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(milestone, field, value)
    milestone.updated_by = user_id
    await db.commit()
    await db.refresh(milestone)
    return milestone


# ===== Stage Record Service =====


async def create_stage_record(
    db: AsyncSession,
    project_id: UUID,
    data: RdStageRecordCreate,
    user_id: UUID | None = None,
) -> RdStageRecord:
    """创建阶段记录"""
    await get_project(db, project_id)
    record = RdStageRecord(
        project_id=project_id,
        **data.model_dump(),
        status="not_started",
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def get_stage_records(db: AsyncSession, project_id: UUID) -> list[RdStageRecord]:
    """获取项目的阶段记录列表"""
    result = await db.execute(
        select(RdStageRecord)
        .where(RdStageRecord.project_id == project_id, ~RdStageRecord.is_deleted)
        .order_by(RdStageRecord.created_at)
    )
    return list(result.scalars().all())


async def update_stage_record(
    db: AsyncSession,
    record_id: UUID,
    data: RdStageRecordUpdate,
    user_id: UUID | None = None,
) -> RdStageRecord:
    """更新阶段记录"""
    result = await db.execute(
        select(RdStageRecord).where(
            RdStageRecord.id == record_id,
            ~RdStageRecord.is_deleted,
        )
    )
    record = result.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="阶段记录不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)
    record.updated_by = user_id
    await db.commit()
    await db.refresh(record)
    return record


# ===== Research Track Service =====


async def create_research_track(
    db: AsyncSession,
    project_id: UUID,
    data: RdResearchTrackCreate,
    user_id: UUID | None = None,
) -> RdResearchTrack:
    """创建研究项"""
    await get_project(db, project_id)
    track = RdResearchTrack(
        project_id=project_id,
        **data.model_dump(),
        status="active",
        conclusion_version=0,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(track)
    await db.commit()
    await db.refresh(track)
    return track


async def get_research_tracks(db: AsyncSession, project_id: UUID) -> list[RdResearchTrack]:
    """获取项目的研究项列表"""
    result = await db.execute(
        select(RdResearchTrack)
        .where(
            RdResearchTrack.project_id == project_id,
            ~RdResearchTrack.is_deleted,
        )
        .order_by(RdResearchTrack.created_at)
    )
    return list(result.scalars().all())


async def update_research_track(
    db: AsyncSession,
    track_id: UUID,
    data: RdResearchTrackUpdate,
    user_id: UUID | None = None,
) -> RdResearchTrack:
    """更新研究项"""
    result = await db.execute(
        select(RdResearchTrack).where(
            RdResearchTrack.id == track_id,
            ~RdResearchTrack.is_deleted,
        )
    )
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="研究项不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(track, field, value)
    track.updated_by = user_id
    await db.commit()
    await db.refresh(track)
    return track


# ===== Research Finding Service =====


async def create_research_finding(
    db: AsyncSession,
    track_id: UUID,
    data: RdResearchFindingCreate,
    user_id: UUID | None = None,
) -> RdResearchFinding:
    """创建研究发现"""
    result = await db.execute(
        select(RdResearchTrack).where(
            RdResearchTrack.id == track_id,
            ~RdResearchTrack.is_deleted,
        )
    )
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="研究项不存在")

    finding = RdResearchFinding(
        track_id=track_id,
        **data.model_dump(),
        version=1,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(finding)
    await db.commit()
    await db.refresh(finding)
    return finding


async def get_research_findings(db: AsyncSession, track_id: UUID) -> list[RdResearchFinding]:
    """获取研究项的发现列表"""
    result = await db.execute(
        select(RdResearchFinding)
        .where(
            RdResearchFinding.track_id == track_id,
            ~RdResearchFinding.is_deleted,
        )
        .order_by(RdResearchFinding.created_at)
    )
    return list(result.scalars().all())


async def update_research_finding(
    db: AsyncSession,
    finding_id: UUID,
    data: RdResearchFindingUpdate,
    user_id: UUID | None = None,
) -> RdResearchFinding:
    """更新研究发现"""
    result = await db.execute(
        select(RdResearchFinding).where(
            RdResearchFinding.id == finding_id,
            ~RdResearchFinding.is_deleted,
        )
    )
    finding = result.scalar_one_or_none()
    if not finding:
        raise HTTPException(status_code=404, detail="研究发现不存在")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(finding, field, value)
    finding.updated_by = user_id
    await db.commit()
    await db.refresh(finding)
    return finding


# ===== Conclusion Version Service =====


async def publish_conclusion_version(
    db: AsyncSession,
    track_id: UUID,
    conclusion: str,
    confidence: str,
    user_id: UUID | None = None,
    change_summary: str | None = None,
    evidence_refs: dict | None = None,  # type: ignore[type-arg]
) -> dict:  # type: ignore[type-arg]
    """发布新的结论版本"""
    result = await db.execute(
        select(RdResearchTrack).where(
            RdResearchTrack.id == track_id,
            ~RdResearchTrack.is_deleted,
        )
    )
    track = result.scalar_one_or_none()
    if not track:
        raise HTTPException(status_code=404, detail="研究项不存在")

    # Increment version
    new_version = (track.conclusion_version or 0) + 1
    track.conclusion_version = new_version
    track.current_conclusion = conclusion
    track.conclusion_confidence = confidence
    track.updated_by = user_id

    # Create version history record
    version_data = {
        "track_id": track_id,
        "version": new_version,
        "conclusion": conclusion,
        "confidence": confidence,
        "change_summary": change_summary,
        "evidence_refs": evidence_refs,
        "author_id": user_id,
    }
    await repo.create_conclusion_version(db, version_data)

    await db.commit()
    await db.refresh(track)

    return {
        "version": track.conclusion_version,
        "conclusion": track.current_conclusion,
        "confidence": track.conclusion_confidence,
        "updated_at": track.updated_at.isoformat() if track.updated_at else None,
    }


async def get_conclusion_history(db: AsyncSession, track_id: UUID) -> list[dict]:  # type: ignore[type-arg]
    """获取研究项的结论版本历史"""
    versions = await repo.get_conclusion_versions(db, track_id)
    return [
        {
            "id": str(v.id),
            "version": v.version,
            "conclusion": v.conclusion,
            "confidence": v.confidence,
            "change_summary": v.change_summary,
            "evidence_refs": v.evidence_refs,
            "author_id": str(v.author_id) if v.author_id else None,
            "created_at": v.created_at.isoformat() if v.created_at else None,
        }
        for v in versions
    ]


# ===== RdProject CRUD Service Functions =====


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
    return await repo.get_rd_projects(
        db,
        stage=stage,
        status=status,
        keyword=keyword,
        project_type=project_type,
        page=page,
        page_size=page_size,
    )


async def create_rd_project(db: AsyncSession, data: RdProjectCreate, user_id: UUID | None = None) -> RdProject:
    """创建 RdProject"""
    project_data = data.model_dump()
    if user_id:
        project_data["created_by"] = user_id
    return await repo.create_rd_project(db, project_data)


async def update_rd_project(
    db: AsyncSession,
    project_id: UUID,
    data: RdProjectUpdate,
    user_id: UUID | None = None,
) -> RdProject:
    """更新 RdProject"""
    project = await get_rd_project(db, project_id)
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_rd_project(db, project, update_data)


async def delete_rd_project(db: AsyncSession, project_id: UUID, user_id: UUID | None = None) -> None:
    """删除 RdProject"""
    project = await get_rd_project(db, project_id)
    await repo.delete_rd_project(db, project)


# ===== Stage Transition Service Functions =====

# 阶段顺序定义
STAGE_ORDER = [
    "initiation",
    "route_dev",
    "optimization",
    "pilot",
    "validation",
    "filing",
]

STAGE_NAMES = {
    "initiation": "立项",
    "route_dev": "打通路线",
    "optimization": "工艺优化",
    "pilot": "中试研究",
    "validation": "工艺验证",
    "filing": "申报资料",
}

# 软门条件定义
SOFT_GATE_CONDITIONS = {
    "initiation": {
        "hard": ["research_completed", "feasibility_passed"],
        "soft": ["candidate_routes >= 1"],
    },
    "route_dev": {
        "hard": ["evaluation_completed", "best_route_confirmed", "safety_assessed"],
        "soft": [],
    },
    "optimization": {
        "hard": ["doe_completed", "cpp_confirmed", "quality_standard_draft"],
        "soft": ["impurity_strategy_draft", "crystal_form_confirmed"],
    },
    "pilot": {
        "hard": ["scale_effect_studied", "engineering_calc_done", "ehs_assessed"],
        "soft": ["impurity_profile_consistent"],
    },
    "validation": {
        "hard": ["three_batches_passed", "process_params_finalized"],
        "soft": ["stability_preliminary_data"],
    },
}


async def check_stage_transition(db: AsyncSession, project_id: UUID, target_stage: str) -> dict:  # type: ignore[type-arg]
    """检查阶段流转条件"""
    project = await get_rd_project(db, project_id)

    # 处理当前阶段为 None 的情况（项目刚创建）
    if project.current_stage is None:
        # 允许流转到第一个阶段（initiation）
        if target_stage == STAGE_ORDER[0]:
            return {
                "allowed": True,
                "current_stage": None,
                "target_stage": target_stage,
                "hard_conditions": {},
                "soft_conditions": {},
                "hard_all_passed": True,
                "soft_all_passed": True,
            }
        else:
            return {
                "allowed": False,
                "reason": f"项目尚未立项，请先流转到{STAGE_NAMES[STAGE_ORDER[0]]}",
            }

    current_stage = project.current_stage

    # 检查阶段顺序
    if target_stage not in STAGE_ORDER:
        return {"allowed": False, "reason": f"无效阶段: {target_stage}"}

    if current_stage not in STAGE_ORDER:
        return {"allowed": False, "reason": f"当前阶段无效: {current_stage}"}

    current_idx = STAGE_ORDER.index(current_stage)
    target_idx = STAGE_ORDER.index(target_stage)

    if target_idx <= current_idx:
        return {"allowed": False, "reason": "目标阶段必须晚于当前阶段"}

    if target_idx != current_idx + 1:
        return {"allowed": False, "reason": "只能流转到下一个阶段"}

    # 获取软门条件
    conditions = SOFT_GATE_CONDITIONS.get(current_stage, {})
    hard_conditions = conditions.get("hard", [])
    soft_conditions = conditions.get("soft", [])

    # TODO: 实际检查这些条件是否满足
    # 目前返回模拟结果
    hard_check = {cond: True for cond in hard_conditions}
    soft_check = {cond: True for cond in soft_conditions}

    all_hard_passed = all(hard_check.values())
    all_soft_passed = all(soft_check.values()) if soft_check else True

    return {
        "allowed": all_hard_passed,
        "current_stage": current_stage,
        "target_stage": target_stage,
        "hard_conditions": hard_check,
        "soft_conditions": soft_check,
        "hard_all_passed": all_hard_passed,
        "soft_all_passed": all_soft_passed,
    }


async def transition_stage(
    db: AsyncSession,
    project_id: UUID,
    target_stage: str,
    review_notes: str | None = None,
    user_id: UUID | None = None,
) -> dict:  # type: ignore[type-arg]
    """执行阶段流转"""
    # 检查流转条件
    check_result = await check_stage_transition(db, project_id, target_stage)

    if not check_result["allowed"]:
        return {"success": False, "message": check_result["reason"]}

    # 更新项目阶段
    project = await get_rd_project(db, project_id)
    update_data = {
        "current_stage": target_stage,
        "updated_by": user_id,
    }
    await repo.update_rd_project(db, project, update_data)

    # 创建新的阶段记录
    stage_data = {
        "project_id": project_id,
        "stage": target_stage,
        "version": 1,
        "status": "active",
        "started_at": datetime.now(UTC),
    }
    if user_id:
        stage_data["created_by"] = user_id

    await repo.create_stage_record(db, stage_data)

    return {
        "success": True,
        "project_id": str(project_id),
        "previous_stage": check_result["current_stage"],
        "new_stage": target_stage,
        "check_result": check_result,
    }


# ===== 中试研究 Service Functions =====


async def get_pilot_studies(db: AsyncSession, project_id: UUID) -> list[RdPilotStudy]:
    """获取项目的中试研究记录"""
    return await repo.get_pilot_studies_by_project(db, project_id)


async def create_pilot_study(db: AsyncSession, data: RdPilotStudyCreate, user_id: UUID | None = None) -> RdPilotStudy:
    """创建中试研究记录"""
    study_data = data.model_dump()
    if user_id:
        study_data["created_by"] = user_id
    return await repo.create_pilot_study(db, study_data)


async def update_pilot_study(
    db: AsyncSession,
    study_id: UUID,
    data: RdPilotStudyUpdate,
    user_id: UUID | None = None,
) -> RdPilotStudy:
    """更新中试研究记录"""
    study = await repo.get_pilot_study_by_id(db, study_id)
    if not study:
        raise NotFoundException("中试研究记录", str(study_id))
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_pilot_study(db, study, update_data)


# ===== 工艺验证 Service Functions =====


async def get_validations(db: AsyncSession, project_id: UUID) -> list[RdProcessValidation]:
    """获取项目的工艺验证记录"""
    return await repo.get_validations_by_project(db, project_id)


async def create_validation(
    db: AsyncSession, data: RdProcessValidationCreate, user_id: UUID | None = None
) -> RdProcessValidation:
    """创建工艺验证记录"""
    validation_data = data.model_dump()
    if user_id:
        validation_data["created_by"] = user_id
    return await repo.create_validation(db, validation_data)


async def update_validation(
    db: AsyncSession,
    validation_id: UUID,
    data: RdProcessValidationUpdate,
    user_id: UUID | None = None,
) -> RdProcessValidation:
    """更新工艺验证记录"""
    validation = await repo.get_validation_by_id(db, validation_id)
    if not validation:
        raise NotFoundException("工艺验证记录", str(validation_id))
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_validation(db, validation, update_data)


# ===== 申报资料 Service Functions =====


async def get_filings(db: AsyncSession, project_id: UUID) -> list[RdRegistrationFiling]:
    """获取项目的申报资料记录"""
    return await repo.get_filings_by_project(db, project_id)


async def create_filing(
    db: AsyncSession, data: RdRegistrationFilingCreate, user_id: UUID | None = None
) -> RdRegistrationFiling:
    """创建申报资料记录"""
    filing_data = data.model_dump()
    if user_id:
        filing_data["created_by"] = user_id
    return await repo.create_filing(db, filing_data)


async def update_filing(
    db: AsyncSession,
    filing_id: UUID,
    data: RdRegistrationFilingUpdate,
    user_id: UUID | None = None,
) -> RdRegistrationFiling:
    """更新申报资料记录"""
    filing = await repo.get_filing_by_id(db, filing_id)
    if not filing:
        raise NotFoundException("申报资料记录", str(filing_id))
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_filing(db, filing, update_data)


# ===== RdStageDeliverable Service Functions =====


async def create_rd_stage_deliverable(
    db: AsyncSession, data: RdStageDeliverableCreate, user_id: UUID | None = None
) -> RdStageDeliverable:
    """创建阶段交付物"""
    deliverable_data = data.model_dump()
    if user_id:
        deliverable_data["created_by"] = user_id
    return await repo.create_rd_stage_deliverable(db, deliverable_data)


async def get_rd_stage_deliverable(db: AsyncSession, deliverable_id: UUID) -> RdStageDeliverable:
    """获取阶段交付物"""
    deliverable = await repo.get_rd_stage_deliverable(db, deliverable_id)
    if not deliverable:
        raise NotFoundException("阶段交付物", str(deliverable_id))
    return deliverable


async def list_rd_stage_deliverables(
    db: AsyncSession,
    project_id: UUID | None = None,
    stage: str | None = None,
    deliverable_type: str | None = None,
    status: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[RdStageDeliverable], int]:
    """获取阶段交付物列表"""
    return await repo.list_rd_stage_deliverables(db, project_id, stage, deliverable_type, status, page, page_size)


async def update_rd_stage_deliverable(
    db: AsyncSession,
    deliverable_id: UUID,
    data: RdStageDeliverableUpdate,
    user_id: UUID | None = None,
) -> RdStageDeliverable:
    """更新阶段交付物"""
    deliverable = await get_rd_stage_deliverable(db, deliverable_id)
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_rd_stage_deliverable(db, deliverable, update_data)


async def delete_rd_stage_deliverable(db: AsyncSession, deliverable_id: UUID, user_id: UUID | None = None) -> None:
    """删除阶段交付物"""
    deliverable = await get_rd_stage_deliverable(db, deliverable_id)
    await repo.delete_rd_stage_deliverable(db, deliverable)


async def delete_pilot_study(db: AsyncSession, study_id: uuid.UUID, user_id: uuid.UUID | None = None) -> None:
    """删除中试研究"""
    await repo.delete_pilot_study(db, study_id, user_id)
    await db.commit()


async def delete_validation(db: AsyncSession, validation_id: uuid.UUID, user_id: uuid.UUID | None = None) -> None:
    """删除工艺验证"""
    await repo.delete_validation(db, validation_id, user_id)
    await db.commit()


async def delete_filing(db: AsyncSession, filing_id: uuid.UUID, user_id: uuid.UUID | None = None) -> None:
    """删除申报资料"""
    await repo.delete_filing(db, filing_id, user_id)
    await db.commit()


# ===== 实验记录 Service =====


async def get_experiment_logs(db: AsyncSession, project_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """获取项目的所有实验记录"""
    return await repo.get_experiment_logs_by_project(db, project_id)


async def create_experiment_log(  # type: ignore[no-untyped-def]
    db: AsyncSession, data, user_id: uuid.UUID | None = None
):
    """创建实验记录"""
    log_data = data.model_dump()
    return await repo.create_experiment_log(db, log_data)


async def update_experiment_log(  # type: ignore[no-untyped-def]
    db: AsyncSession, log_id: uuid.UUID, data, user_id: uuid.UUID | None = None
):
    """更新实验记录"""
    log = await repo.get_experiment_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="实验记录不存在")
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_experiment_log(db, log, update_data)


async def delete_experiment_log(db: AsyncSession, log_id: uuid.UUID, user_id: uuid.UUID | None = None) -> None:
    """删除实验记录"""
    await repo.delete_experiment_log(db, log_id, user_id)
    await db.commit()


# ===== 研发报告 Service =====


async def get_reports(db: AsyncSession, project_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """获取项目的所有研发报告"""
    return await repo.get_reports_by_project(db, project_id)


async def create_report(db: AsyncSession, data, user_id: uuid.UUID | None = None):  # type: ignore[no-untyped-def]
    """创建研发报告"""
    report_data = data.model_dump()
    if user_id:
        report_data["author_id"] = user_id
    return await repo.create_report(db, report_data)


async def update_report(  # type: ignore[no-untyped-def]
    db: AsyncSession, report_id: uuid.UUID, data, user_id: uuid.UUID | None = None
):
    """更新研发报告"""
    report = await repo.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_report(db, report, update_data)


async def delete_report(db: AsyncSession, report_id: uuid.UUID, user_id: uuid.UUID | None = None) -> None:
    """删除研发报告"""
    await repo.delete_report(db, report_id, user_id)
    await db.commit()


# ===== 立项申请 Service =====


async def get_initiations(db: AsyncSession, project_id: uuid.UUID):  # type: ignore[no-untyped-def]
    """获取项目的所有立项申请"""
    return await repo.get_initiations_by_project(db, project_id)


async def create_initiation(db: AsyncSession, data, user_id: uuid.UUID | None = None):  # type: ignore[no-untyped-def]
    """创建立项申请"""
    initiation_data = data.model_dump()
    if user_id:
        initiation_data["applicant_id"] = user_id
    return await repo.create_initiation(db, initiation_data)


async def update_initiation(  # type: ignore[no-untyped-def]
    db: AsyncSession, initiation_id: uuid.UUID, data, user_id: uuid.UUID | None = None
):
    """更新立项申请"""
    initiation = await repo.get_initiation_by_id(db, initiation_id)
    if not initiation:
        raise HTTPException(status_code=404, detail="立项申请不存在")
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_initiation(db, initiation, update_data)


async def delete_initiation(db: AsyncSession, initiation_id: uuid.UUID, user_id: uuid.UUID | None = None) -> None:
    """删除立项申请"""
    await repo.delete_initiation(db, initiation_id, user_id)
    await db.commit()


# ===== 交付物模板 Service =====


async def get_deliverable_templates(  # type: ignore[no-untyped-def]
    db: AsyncSession,
    stage: str | None = None,
    deliverable_type: str | None = None,
    is_active: bool | None = None,
):
    """获取交付物模板列表"""
    return await repo.get_deliverable_templates(db, stage, deliverable_type, is_active)


async def create_deliverable_template(  # type: ignore[no-untyped-def]
    db: AsyncSession, data, user_id: uuid.UUID | None = None
):
    """创建交付物模板"""
    template_data = data.model_dump()
    if user_id:
        template_data["creator_id"] = user_id
    return await repo.create_deliverable_template(db, template_data)


async def update_deliverable_template(  # type: ignore[no-untyped-def]
    db: AsyncSession, template_id: uuid.UUID, data, user_id: uuid.UUID | None = None
):
    """更新交付物模板"""
    template = await repo.get_deliverable_template_by_id(db, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")
    update_data = data.model_dump(exclude_unset=True)
    if user_id:
        update_data["updated_by"] = user_id
    return await repo.update_deliverable_template(db, template, update_data)


async def delete_deliverable_template(
    db: AsyncSession, template_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除交付物模板"""
    await repo.delete_deliverable_template(db, template_id, user_id)
    await db.commit()


# ===== AI 报告生成 Service =====


async def generate_report_with_ai(
    db: AsyncSession,
    project_id: uuid.UUID,
    deliverable_type: str,
    template_id: uuid.UUID | None = None,
    additional_context: str | None = None,
) -> dict:  # type: ignore[type-arg]
    """使用 AI 生成报告"""
    from app.core.llm import llm_client
    from app.core.llm.exceptions import LLMOutputError, LLMProviderError, LLMRateLimitError
    from app.modules.research.models import (
        RdProject,
        RdResearchFinding,
        RdResearchTrack,
    )

    # 1. 获取项目信息
    project_result = await db.execute(select(RdProject).where(RdProject.id == project_id, ~RdProject.is_deleted))
    project = project_result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="项目不存在")

    # 2. 获取模板（如果有）
    template_content = ""
    if template_id:
        template = await repo.get_deliverable_template_by_id(db, template_id)
        if template and template.template_content:
            template_content = template.template_content

    # 3. 收集项目数据
    data_sources = []

    # 获取研究项
    tracks_result = await db.execute(
        select(RdResearchTrack).where(
            RdResearchTrack.project_id == project_id,
            ~RdResearchTrack.is_deleted,
        )
    )
    tracks = tracks_result.scalars().all()

    track_summaries = []
    for track in tracks:
        # 获取研究发现
        findings_result = await db.execute(
            select(RdResearchFinding).where(
                RdResearchFinding.track_id == track.id,
                ~RdResearchFinding.is_deleted,
            )
        )
        findings = findings_result.scalars().all()

        findings_text = "\n".join(
            [f"- {f.finding_type}: {f.conclusion or '无结论'} (置信度: {f.confidence})" for f in findings]
        )

        track_summaries.append(f"""
研究项: {track.name}
类型: {track.type}
状态: {track.status}
当前结论: {track.current_conclusion or "暂无"}
研究发现:
{findings_text}
""")
        data_sources.append(f"研究项: {track.name}")

    # 获取实验记录
    experiments_result = await db.execute(
        select(RdExperimentLog).where(
            RdExperimentLog.project_id == project_id,
            ~RdExperimentLog.is_deleted,
        )
    )
    experiments = experiments_result.scalars().all()

    experiment_summaries = []
    for exp in experiments:
        experiment_summaries.append(f"""
实验: {exp.title}
类型: {exp.experiment_type}
日期: {exp.experiment_date}
操作人: {exp.operator}
目的: {exp.objective or "无"}
步骤: {exp.procedure or "无"}
现象: {exp.observations or "无"}
结论: {exp.conclusion or "无"}
""")
        data_sources.append(f"实验: {exp.title}")

    # 4. 构建提示词
    deliverable_type_names = {
        "literature_review": "技术调研报告",
        "development_plan": "研发总方案",
        "route_confirmation": "工艺路线确认报告",
        "safety_assessment": "工艺安全评估报告",
        "impurity_analysis": "理论杂质分析",
        "optimization_plan": "小试工艺优化方案",
        "optimization_report": "小试工艺优化报告",
        "scale_up_summary": "公斤级放大总结报告",
        "pilot_plan": "中试方案",
        "pilot_report": "中试报告",
        "supplier_development": "供应商开发报告",
        "validation_plan": "工艺验证方案",
        "validation_report": "工艺验证报告",
        "cleaning_procedure": "清洁操作规程和记录",
        "cleaning_validation": "清洁验证总结报告",
        "structure_confirmation": "原料药结构确证报告",
        "crystal_form_study": "晶型和粒度研究报告",
        "impurity_study": "杂质研究报告",
    }

    deliverable_name = deliverable_type_names.get(deliverable_type, deliverable_type)

    prompt = f"""你是一位专业的原料药研发专家。请根据以下项目信息，生成一份{deliverable_name}。

项目信息:
- 项目名称: {project.name}
- API 名称: {project.api_name}
- CAS 号: {project.cas_number or "无"}
- 分子式: {project.molecular_formula or "无"}
- 分子量: {project.molecular_weight or "无"}
- 适应症: {project.indication or "无"}
- 当前阶段: {project.current_stage}

研究项数据:
{"".join(track_summaries) if track_summaries else "暂无研究项数据"}

实验记录数据:
{"".join(experiment_summaries) if experiment_summaries else "暂无实验记录数据"}

{f"模板参考:\n{template_content}" if template_content else ""}

{f"额外要求:\n{additional_context}" if additional_context else ""}

请生成一份专业、完整的{deliverable_name}，包含以下部分:
1. 概述
2. 项目背景
3. 研究内容与方法
4. 主要发现与结果
5. 分析与讨论
6. 结论与建议

请使用 Markdown 格式输出。"""

    # 5. 调用 LLM
    try:
        result = await llm_client.chat(
            [
                {
                    "role": "system",
                    "content": "你是一位专业的原料药研发专家，擅长撰写各类研发报告。",
                },
                {"role": "user", "content": prompt},
            ]
        )

        return {
            "content": result,
            "structure": None,
            "data_sources": data_sources,
        }
    except (LLMOutputError, LLMProviderError, LLMRateLimitError):
        logger.exception("LLM call failed")
        return {
            "content": "AI 分析暂时不可用，请人工审核",
            "structure": None,
            "data_sources": data_sources,
        }
    except Exception as e:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)}")


# ===== AI 报告生成 Service =====


async def generate_deliverable_report(
    db: AsyncSession, project_id: uuid.UUID, deliverable_template_id: uuid.UUID
) -> str:
    """根据交付物模板和项目数据生成报告 (MVP 严谨版)"""

    # 1. 获取模板
    result = await db.execute(select(RdDeliverableTemplate).where(RdDeliverableTemplate.id == deliverable_template_id))
    template = result.scalar_one_or_none()
    if not template or not template.template_content:
        raise ValueError("模板不存在或内容为空")

    # 2. 构建 Fact 字典 (Type A)
    facts = await build_fact_dictionary(db, project_id, template.stage)

    # 3. 计算派生结论 (Type B)
    # 这里以获取第一个工艺优化任务的 DOE 数据为例
    opt_result = await db.execute(
        select(ProcessOptimization).where(ProcessOptimization.project_id == project_id).limit(1)
    )
    optimization = opt_result.scalar_one_or_none()
    derived_facts = {}
    if optimization and optimization.doe_experiment:
        derived_facts = calculate_doe_conclusions(optimization.doe_experiment)

    # 4. 执行槽位填充
    pre_filled_text, prose_slots = fill_template_slots(template.template_content, facts, derived_facts)

    # 5. 调用 LLM 填充 Prose 槽位 (Type C)
    # 简化处理：如果存在 Prose 槽位，则调用 LLM 补全
    final_report = pre_filled_text
    if prose_slots:
        from app.core.llm import llm_client

        prompt = f"""
        请根据以下已填充好事实数据的报告草稿，补全其中的逻辑连接和讨论部分。
        注意：不要修改任何已经存在的数字和事实描述。

        草稿内容：
        {pre_filled_text[:3000]}
        """
        try:
            messages = [
                {"role": "system", "content": "你是制药研发专家，负责润色报告。"},
                {"role": "user", "content": prompt},
            ]
            response = await llm_client.chat_completion(messages)
            final_report = response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM 补全失败: {e}")
            # 如果 LLM 失败，至少返回已填充事实的草稿

    return final_report


# ===== Fact 字典构建器 =====


async def build_fact_dictionary(db: AsyncSession, project_id: uuid.UUID, stage: str) -> dict:
    """
    构建用于报告生成的 Fact 字典。
    包含：项目基本信息 + 当前阶段的关键实验数据。
    """
    facts = {}

    # 1. 获取项目基本信息 (Type A: Fact)
    proj_result = await db.execute(select(RdProject).where(RdProject.id == project_id))
    project = proj_result.scalar_one_or_none()
    if project:
        facts["project_name"] = {"value": project.name, "unit": "", "source_id": str(project.id)}
        facts["api_name"] = {"value": project.api_name, "unit": "", "source_id": str(project.id)}
        facts["cas_number"] = {"value": project.cas_number, "unit": "", "source_id": str(project.id)}
        facts["molecular_formula"] = {"value": project.molecular_formula, "unit": "", "source_id": str(project.id)}

    # 2. 获取当前阶段的工艺优化数据 (以 DOE 为例)
    if stage == "process_optimization":
        opt_result = await db.execute(
            select(ProcessOptimization)
            .where(ProcessOptimization.project_id == project_id, ProcessOptimization.status != "failed")
            .order_by(ProcessOptimization.updated_at.desc())
            .limit(1)
        )
        optimization = opt_result.scalar_one_or_none()

        if optimization and optimization.doe_experiment:
            doe_data = optimization.doe_experiment
            # 提取关键事实
            if "analysis_result" in doe_data and "optimal_conditions" in doe_data["analysis_result"]:
                optimal = doe_data["analysis_result"]["optimal_conditions"]
                for param, val in optimal.items():
                    key = f"doe_optimal_{param}"
                    facts[key] = {"value": val, "unit": _get_unit_for_param(param), "source_id": optimization.id}

            if "analysis_result" in doe_data and "r_squared" in doe_data["analysis_result"]:
                facts["doe_r_squared"] = {
                    "value": doe_data["analysis_result"]["r_squared"],
                    "unit": "",
                    "source_id": optimization.id,
                }

    # 3. 获取杂质研究数据 (Type A: Fact)
    track_result = await db.execute(
        select(RdResearchTrack).where(RdResearchTrack.project_id == project_id, RdResearchTrack.type == "impurity")
    )
    impurity_track = track_result.scalar_one_or_none()
    if impurity_track and impurity_track.current_conclusion:
        # 这里可以进一步解析 conclusion 或关联的 findings
        facts["impurity_conclusion_summary"] = {
            "value": impurity_track.current_conclusion[:100] + "...",
            "unit": "",
            "source_id": str(impurity_track.id),
        }

    return facts


def _get_unit_for_param(param_name: str) -> str:
    """简单的单位映射，实际生产中应从元数据中获取"""
    unit_map = {"temperature": "°C", "pressure": "bar", "time": "h", "yield": "%"}
    return unit_map.get(param_name.lower(), "")


# ===== 派生结论计算器 (Derived Fact Calculator) =====


def calculate_doe_conclusions(doe_data: dict) -> dict:
    """
    根据 DOE 实验数据计算派生结论。
    输入: doe_data (包含 runs, factors, responses)
    输出: 结构化结论标签字典
    """
    conclusions = {}

    if not doe_data or "runs" not in doe_data:
        return conclusions

    runs = doe_data["runs"]
    responses = doe_data.get("responses", [])

    # 1. 计算各响应的极值和趋势
    for resp in responses:
        resp_name = resp["name"]
        values = [run["response_values"].get(resp_name) for run in runs if run["status"] == "completed"]

        if not values:
            continue

        valid_values = [v for v in values if v is not None]
        if not valid_values:
            continue

        max_val = max(valid_values)
        min_val = min(valid_values)
        avg_val = sum(valid_values) / len(valid_values)

        # 简单的趋势判断 (实际应结合因子水平分析)
        if max_val - min_val < 0.01 * avg_val:
            trend = "stable"
        elif valid_values[-1] > valid_values[0]:
            trend = "increasing"
        else:
            trend = "decreasing"

        conclusions[f"{resp_name}_summary"] = {
            "max": max_val,
            "min": min_val,
            "avg": round(avg_val, 2),
            "trend": trend,
            "unit": resp.get("unit", ""),
        }

    # 2. 提取最优条件 (如果分析结果中已有)
    if "analysis_result" in doe_data and "optimal_conditions" in doe_data["analysis_result"]:
        optimal = doe_data["analysis_result"]["optimal_conditions"]
        conclusions["optimal_conditions_labels"] = {
            k: {"value": v, "desc": f"The optimal level for {k} is {v}"} for k, v in optimal.items()
        }

    # 3. 模型拟合度评价
    if "analysis_result" in doe_data and "r_squared" in doe_data["analysis_result"]:
        r2 = doe_data["analysis_result"]["r_squared"]
        fit_quality = "excellent" if r2 > 0.9 else ("good" if r2 > 0.7 else "poor")
        conclusions["model_fit_evaluation"] = {"r_squared": r2, "quality_label": fit_quality}

    return conclusions


# ===== 槽位填充引擎 (Slot Filling Engine) =====


def fill_template_slots(template_content: str, facts: dict, derived_facts: dict) -> tuple[str, list[str]]:
    """
    填充模板中的 Fact 和 Derived Fact 槽位。
    返回: (填充后的文本, 剩余的 Prose 槽位列表)
    """
    filled_text = template_content
    prose_slots = []

    # 1. 填充 Fact 槽位 {{F:key}}
    def replace_fact(match):
        key = match.group(1)
        if key in facts:
            item = facts[key]
            value = item["value"]
            unit = item.get("unit", "")
            # 格式化输出，例如: 85.3%
            return f"{value}{unit}" if unit else str(value)
        return match.group(0)  # 如果找不到，保留原样

    filled_text = re.sub(r"\{\{F:(\w+)\}\}", replace_fact, filled_text)

    # 2. 填充 Derived Fact 槽位 {{B:key}}
    # 这里我们简单地将结论标签转化为自然语言片段
    def replace_derived(match):
        key = match.group(1)
        if key in derived_facts:
            data = derived_facts[key]
            # 根据 key 的类型进行简单的自然语言转化
            if "summary" in key and isinstance(data, dict):
                return f"{data['trend']} (范围: {data['min']}-{data['max']}{data.get('unit', '')})"
            elif "quality_label" in data:
                return f"模型拟合度为 {data['quality_label']} (R²={data['r_squared']})"
            return str(data)
        return match.group(0)

    filled_text = re.sub(r"\{\{B:(\w+)\}\}", replace_derived, filled_text)

    # 3. 提取剩余的 Prose 槽位 {{P:key}}
    prose_slots = re.findall(r"\{\{P:(\w+)\}\}", filled_text)

    return filled_text, prose_slots


# ===== 数值校验层 (Validation Layer) =====


def validate_report_content(report: str, facts: dict) -> dict:
    """
    对生成的报告进行确定性校验。
    返回: {"passed": bool, "errors": list}
    """
    errors = []

    # 1. 数值一致性校验
    # 提取报告中所有的数字（简单正则）
    numbers_in_report = re.findall(r"\d+\.?\d*", report)

    for key, item in facts.items():
        val_str = str(item["value"])
        if val_str not in numbers_in_report and len(val_str) > 1:
            # 如果重要事实值没出现在报告里，记为警告
            errors.append(f"Warning: Fact '{key}' ({val_str}) might be missing from the report.")

    # 2. 术语合法性校验 (示例)
    forbidden_terms = ["大概", "可能", "也许"]  # 研发报告应避免模糊词汇
    for term in forbidden_terms:
        if term in report:
            errors.append(f"Term alert: Found informal term '{term}'.")

    return {"passed": len([e for e in errors if "Alert" in e]) == 0, "warnings": errors}
