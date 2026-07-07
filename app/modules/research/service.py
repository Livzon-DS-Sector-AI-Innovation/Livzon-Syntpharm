"""Research business workflows."""

import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import DuplicateException, NotFoundException
from app.modules.research import repository as repo
from app.modules.research.models import (
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
from app.modules.research.schemas import (
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


async def create_project(
    db: AsyncSession, data: ResearchProjectCreate
) -> ResearchProject:
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
            not RdProject.is_deleted,
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
    if "project_no" in update_data and update_data["project_no"] != project.project_no:
        if await repo.exists_by_project_no(
            db, update_data["project_no"], exclude_id=project_id
        ):
            raise DuplicateException("项目编号", update_data["project_no"])
    return await repo.update_project(db, project, update_data)


async def delete_project(db: AsyncSession, project_id: uuid.UUID) -> None:
    project = await get_project(db, project_id)
    await repo.delete_project(db, project)


# ICH Analysis functions
from sqlalchemy import func, select

from app.modules.research.models import ICHAnalysisRecord


async def analyze_ich_q3c(
    db: AsyncSession,
    file_content: bytes,
    filename: str,
    route: str | None = None,
) -> dict:
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
) -> dict:
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
        .where(RdMilestone.project_id == project_id, not RdMilestone.is_deleted)
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
            RdMilestone.id == milestone_id, not RdMilestone.is_deleted
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
        .where(RdStageRecord.project_id == project_id, not RdStageRecord.is_deleted)
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
            RdStageRecord.id == record_id, not RdStageRecord.is_deleted
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


async def get_research_tracks(
    db: AsyncSession, project_id: UUID
) -> list[RdResearchTrack]:
    """获取项目的研究项列表"""
    result = await db.execute(
        select(RdResearchTrack)
        .where(
            RdResearchTrack.project_id == project_id,
            not RdResearchTrack.is_deleted,
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
            RdResearchTrack.id == track_id, not RdResearchTrack.is_deleted
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
            RdResearchTrack.id == track_id, not RdResearchTrack.is_deleted
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


async def get_research_findings(
    db: AsyncSession, track_id: UUID
) -> list[RdResearchFinding]:
    """获取研究项的发现列表"""
    result = await db.execute(
        select(RdResearchFinding)
        .where(
            RdResearchFinding.track_id == track_id,
            not RdResearchFinding.is_deleted,
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
            RdResearchFinding.id == finding_id, not RdResearchFinding.is_deleted
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
    evidence_refs: dict | None = None,
) -> dict:
    """发布新的结论版本"""
    result = await db.execute(
        select(RdResearchTrack).where(
            RdResearchTrack.id == track_id, not RdResearchTrack.is_deleted
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


async def get_conclusion_history(db: AsyncSession, track_id: UUID) -> list[dict]:
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


async def create_rd_project(
    db: AsyncSession, data: RdProjectCreate, user_id: UUID | None = None
) -> RdProject:
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


async def delete_rd_project(
    db: AsyncSession, project_id: UUID, user_id: UUID | None = None
) -> None:
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


async def check_stage_transition(
    db: AsyncSession, project_id: UUID, target_stage: str
) -> dict:
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
) -> dict:
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


async def create_pilot_study(
    db: AsyncSession, data: RdPilotStudyCreate, user_id: UUID | None = None
) -> RdPilotStudy:
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


async def get_validations(
    db: AsyncSession, project_id: UUID
) -> list[RdProcessValidation]:
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


async def get_rd_stage_deliverable(
    db: AsyncSession, deliverable_id: UUID
) -> RdStageDeliverable:
    """获取阶段交付物"""
    return await repo.get_rd_stage_deliverable(db, deliverable_id)


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
    return await repo.list_rd_stage_deliverables(
        db, project_id, stage, deliverable_type, status, page, page_size
    )


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


async def delete_rd_stage_deliverable(
    db: AsyncSession, deliverable_id: UUID, user_id: UUID | None = None
) -> None:
    """删除阶段交付物"""
    deliverable = await get_rd_stage_deliverable(db, deliverable_id)
    await repo.delete_rd_stage_deliverable(db, deliverable)


async def delete_pilot_study(
    db: AsyncSession, study_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除中试研究"""
    await repo.delete_pilot_study(db, study_id, user_id)
    await db.commit()


async def delete_validation(
    db: AsyncSession, validation_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除工艺验证"""
    await repo.delete_validation(db, validation_id, user_id)
    await db.commit()


async def delete_filing(
    db: AsyncSession, filing_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除申报资料"""
    await repo.delete_filing(db, filing_id, user_id)
    await db.commit()


# ===== 实验记录 Service =====


async def get_experiment_logs(db: AsyncSession, project_id: uuid.UUID):
    """获取项目的所有实验记录"""
    return await repo.get_experiment_logs_by_project(db, project_id)


async def create_experiment_log(
    db: AsyncSession, data, user_id: uuid.UUID | None = None
):
    """创建实验记录"""
    log_data = data.model_dump()
    return await repo.create_experiment_log(db, log_data)


async def update_experiment_log(
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


async def delete_experiment_log(
    db: AsyncSession, log_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除实验记录"""
    await repo.delete_experiment_log(db, log_id, user_id)
    await db.commit()


# ===== 研发报告 Service =====


async def get_reports(db: AsyncSession, project_id: uuid.UUID):
    """获取项目的所有研发报告"""
    return await repo.get_reports_by_project(db, project_id)


async def create_report(db: AsyncSession, data, user_id: uuid.UUID | None = None):
    """创建研发报告"""
    report_data = data.model_dump()
    if user_id:
        report_data["author_id"] = user_id
    return await repo.create_report(db, report_data)


async def update_report(
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


async def delete_report(
    db: AsyncSession, report_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除研发报告"""
    await repo.delete_report(db, report_id, user_id)
    await db.commit()


# ===== 立项申请 Service =====


async def get_initiations(db: AsyncSession, project_id: uuid.UUID):
    """获取项目的所有立项申请"""
    return await repo.get_initiations_by_project(db, project_id)


async def create_initiation(db: AsyncSession, data, user_id: uuid.UUID | None = None):
    """创建立项申请"""
    initiation_data = data.model_dump()
    if user_id:
        initiation_data["applicant_id"] = user_id
    return await repo.create_initiation(db, initiation_data)


async def update_initiation(
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


async def delete_initiation(
    db: AsyncSession, initiation_id: uuid.UUID, user_id: uuid.UUID | None = None
) -> None:
    """删除立项申请"""
    await repo.delete_initiation(db, initiation_id, user_id)
    await db.commit()


# ===== 交付物模板 Service =====


async def get_deliverable_templates(
    db: AsyncSession,
    stage: str | None = None,
    deliverable_type: str | None = None,
    is_active: bool | None = None,
):
    """获取交付物模板列表"""
    return await repo.get_deliverable_templates(db, stage, deliverable_type, is_active)


async def create_deliverable_template(
    db: AsyncSession, data, user_id: uuid.UUID | None = None
):
    """创建交付物模板"""
    template_data = data.model_dump()
    if user_id:
        template_data["creator_id"] = user_id
    return await repo.create_deliverable_template(db, template_data)


async def update_deliverable_template(
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
) -> dict:
    """使用 AI 生成报告"""
    from app.core.llm import llm_client
    from app.modules.research.models import (
        RdProject,
        RdResearchFinding,
        RdResearchTrack,
    )

    # 1. 获取项目信息
    project_result = await db.execute(
        select(RdProject).where(RdProject.id == project_id, not RdProject.is_deleted)
    )
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
            not RdResearchTrack.is_deleted,
        )
    )
    tracks = tracks_result.scalars().all()

    track_summaries = []
    for track in tracks:
        # 获取研究发现
        findings_result = await db.execute(
            select(RdResearchFinding).where(
                RdResearchFinding.track_id == track.id,
                not RdResearchFinding.is_deleted,
            )
        )
        findings = findings_result.scalars().all()

        findings_text = "\n".join(
            [
                f"- {f.finding_type}: {f.conclusion or '无结论'} (置信度: {f.confidence})"
                for f in findings
            ]
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
            not RdExperimentLog.is_deleted,
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
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 生成失败: {str(e)}")
