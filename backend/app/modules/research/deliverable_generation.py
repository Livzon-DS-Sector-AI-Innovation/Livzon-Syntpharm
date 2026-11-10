"""阶段交付文档 → AI 生成研发报告（编排层）。

这一层只负责「把已有能力串起来」，不重写生成逻辑：

1. 按 ``stage + deliverable_type`` 推导预填值（标题、版本、受控编码）与模板候选；
2. 找到或补建 ``RdStageDeliverable``、找到或补建 ``RdReport``；
3. 调 ``report_gen.service.create_job`` 提交现有的异步生成任务；
4. 回写 ``report_id`` / ``report_gen_job_id``，并在任务完成后把 docx 落进附件目录。

生成引擎（Agent 循环、槽位、渲染）完全复用，本模块不碰。
"""

from __future__ import annotations

import logging
import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, NotFoundException
from app.modules.research import deliverable_files
from app.modules.research.doc_template import store as artifact_store
from app.modules.research.models import (
    RdDeliverableTemplate,
    RdDeliverableTemplateVersion,
    RdProject,
    RdReport,
    RdReportGenJob,
    RdStageDeliverable,
)
from app.modules.research.report_gen.schemas import ReportGenJobCreateRequest
from app.modules.research.report_gen.service import create_job as create_report_gen_job
from app.modules.research.schemas import (
    DELIVERABLE_TYPES,
    RdDeliverableTemplateOption,
    RdStageDeliverableGenerateRequest,
    RdStageDeliverableGenerateResult,
    RdStageDeliverableGenerationBrief,
    RdStageDeliverableGenerationOptions,
    RdStageDeliverableGenerationStatus,
    RdStageDeliverableReportLink,
)

logger = logging.getLogger(__name__)

# 阶段中文名与前端 STAGE_LABELS 保持一致：默认标题直接用它拼，避免两处文案分叉
STAGE_LABELS: dict[str, str] = {
    "initiation": "立项",
    "route_dev": "打通路线",
    "optimization": "工艺优化",
    "pilot": "中试研究",
    "validation": "工艺验证",
    "filing": "申报资料",
}

_STAGE_CODES: dict[str, str] = {
    "initiation": "01",
    "route_dev": "02",
    "optimization": "03",
    "pilot": "04",
    "validation": "05",
    "filing": "06",
}

# 任务还在跑：向导打开时若命中，直接跳到第 3 步看进度，不重复提交
ACTIVE_JOB_STATUSES: tuple[str, ...] = ("queued", "running")

# 「有附件」才算已经出过稿：这种记录再生成时另起一条版本行，历史仍可查。
# 注意不能用 status 判断——提交任务就会把状态置 in_progress，用状态会把「点了但没出稿」
# 的记录误判成已生成，每点一次就多一条空版本行。
def _has_output(deliverable: RdStageDeliverable | None) -> bool:
    return bool(deliverable is not None and deliverable.file_name)

_VERSION_RE = re.compile(r"^[vV]?(\d+)\.(\d+)$")


def stage_label(stage: str) -> str:
    return STAGE_LABELS.get(stage, stage)


def deliverable_type_label(deliverable_type: str) -> str:
    """把 ``development_plan`` 翻成中文；未知类型不暴露英文键。"""
    for items in DELIVERABLE_TYPES.values():
        for item in items:
            if item["type"] == deliverable_type:
                return str(item["label"])
    return "其他类型"


def _validate_stage_type(stage: str, deliverable_type: str) -> None:
    types = DELIVERABLE_TYPES.get(stage)
    if types is None:
        raise BadRequestException(f"未知的研发阶段：{stage}")
    if deliverable_type not in {item["type"] for item in types}:
        raise BadRequestException(f"「{deliverable_type}」不属于 {stage_label(stage)} 阶段")


def _default_title(project: RdProject, stage: str, deliverable_type: str) -> str:
    return f"{project.name} - {stage_label(stage)} - {deliverable_type_label(deliverable_type)}"


def _default_doc_code(stage: str, deliverable_type: str) -> str:
    """受控编码占位：``RD-阶段序号-类型序号``。项目主表没有项目编号，只能按阶段+类型给。"""
    type_index = 1
    for index, item in enumerate(DELIVERABLE_TYPES.get(stage, []), start=1):
        if item["type"] == deliverable_type:
            type_index = index
            break
    return f"RD-{_STAGE_CODES.get(stage, '00')}-{type_index:02d}"


def _next_version(current: str | None) -> str:
    """v1.0 → v1.1；认不出的历史值追加后缀，不丢用户填的原文。"""
    if not current:
        return "v1.0"
    matched = _VERSION_RE.match(current.strip())
    if not matched:
        return f"{current.strip()}-v2"
    return f"v{int(matched.group(1))}.{int(matched.group(2)) + 1}"


def _job_brief(job: RdReportGenJob | None) -> RdStageDeliverableGenerationBrief | None:
    """任务 → 行内/向导用的状态简报；无任务时返回 None。"""
    if job is None:
        return None
    return RdStageDeliverableGenerationBrief(
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        error_message=job.error_message,
        slot_total=job.slot_total,
        slot_filled=job.slot_filled,
        slot_gap=job.slot_gap,
        document_ready=bool(job.document_object_key),
    )


async def _load_project(session: AsyncSession, project_id: uuid.UUID) -> RdProject:
    project = await session.get(RdProject, project_id)
    if project is None or project.is_deleted:
        raise NotFoundException("研发项目", str(project_id))
    return project


async def _templates_of_stage(session: AsyncSession, stage: str) -> list[RdDeliverableTemplate]:
    result = await session.execute(
        select(RdDeliverableTemplate)
        .where(
            RdDeliverableTemplate.is_deleted.is_(False),
            RdDeliverableTemplate.is_active.is_(True),
            RdDeliverableTemplate.stage == stage,
        )
        .order_by(RdDeliverableTemplate.created_at.desc())
    )
    return list(result.scalars().all())


async def _current_version_numbers(session: AsyncSession, template_ids: list[uuid.UUID]) -> dict[uuid.UUID, int]:
    """批量取当前版本号：列表页一次查询，避免逐个模板查版本表。"""
    if not template_ids:
        return {}
    result = await session.execute(
        select(RdDeliverableTemplateVersion.template_id, RdDeliverableTemplateVersion.version_no).where(
            RdDeliverableTemplateVersion.template_id.in_(template_ids),
            RdDeliverableTemplateVersion.is_current.is_(True),
            RdDeliverableTemplateVersion.is_deleted.is_(False),
        )
    )
    return {row[0]: row[1] for row in result.all()}


def _to_template_options(
    templates: list[RdDeliverableTemplate],
    version_numbers: dict[uuid.UUID, int],
    deliverable_type: str,
) -> tuple[list[RdDeliverableTemplateOption], uuid.UUID | None]:
    """精确匹配优先、有母本的优先。

    推荐项只能是「类型精确匹配 + 已上传母本」：降级候选（同阶段其它类型）只用来
    让用户知道阶段里有什么模板，绝不替用户选一个类型不对的母本去出稿。
    """
    options: list[RdDeliverableTemplateOption] = []
    for template in templates:
        options.append(
            RdDeliverableTemplateOption(
                id=template.id,
                name=template.name,
                deliverable_type=template.deliverable_type,
                stage=template.stage,
                version_no=version_numbers.get(template.id),
                file_name=template.file_name,
                has_file=bool(template.file_object_key),
                is_exact_match=template.deliverable_type == deliverable_type,
                is_recommended=False,
            )
        )
    # 精确匹配在前、有母本在前、版本新的在前：用户看到的第一个就是该用的
    options.sort(
        key=lambda item: (
            not item.is_exact_match,
            not item.has_file,
            -(item.version_no or 0),
            item.name,
        )
    )
    recommended = next((item for item in options if item.is_exact_match and item.has_file), None)
    if recommended is not None:
        recommended.is_recommended = True
    return options, (recommended.id if recommended else None)


async def _template_candidates(
    session: AsyncSession, stage: str, deliverable_type: str
) -> tuple[list[RdDeliverableTemplateOption], uuid.UUID | None]:
    """模板候选：精确匹配优先；一个都没有时降级展示同阶段其它类型，供用户判断。

    降级只影响「展示什么」，不产生推荐值——上层会因此走到「去上传模板」的提示分支。
    """
    stage_templates = await _templates_of_stage(session, stage)
    exact = [item for item in stage_templates if item.deliverable_type == deliverable_type]
    chosen = exact or stage_templates
    version_numbers = await _current_version_numbers(session, [item.id for item in chosen])
    return _to_template_options(chosen, version_numbers, deliverable_type)


async def _latest_deliverable(
    session: AsyncSession, project_id: uuid.UUID, stage: str, deliverable_type: str
) -> RdStageDeliverable | None:
    result = await session.execute(
        select(RdStageDeliverable)
        .where(
            RdStageDeliverable.is_deleted.is_(False),
            RdStageDeliverable.project_id == project_id,
            RdStageDeliverable.stage == stage,
            RdStageDeliverable.deliverable_type == deliverable_type,
        )
        .order_by(RdStageDeliverable.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def _load_deliverable(session: AsyncSession, deliverable_id: uuid.UUID) -> RdStageDeliverable:
    deliverable = await session.get(RdStageDeliverable, deliverable_id)
    if deliverable is None or deliverable.is_deleted:
        raise NotFoundException("阶段交付物", str(deliverable_id))
    return deliverable


async def _job_of_deliverable(session: AsyncSession, deliverable: RdStageDeliverable) -> RdReportGenJob | None:
    """优先取这条记录挂的任务；老数据没挂 job 时再按报告找最近一条。"""
    if deliverable.report_gen_job_id:
        job = await session.get(RdReportGenJob, deliverable.report_gen_job_id)
        if job is not None and not job.is_deleted:
            return job
    if deliverable.report_id:
        result = await session.execute(
            select(RdReportGenJob)
            .where(
                RdReportGenJob.is_deleted.is_(False),
                RdReportGenJob.report_id == deliverable.report_id,
            )
            .order_by(RdReportGenJob.created_at.desc())
            .limit(1)
        )
        return result.scalars().first()
    return None


async def _active_job_of_report(session: AsyncSession, report_id: uuid.UUID) -> RdReportGenJob | None:
    result = await session.execute(
        select(RdReportGenJob)
        .where(
            RdReportGenJob.is_deleted.is_(False),
            RdReportGenJob.report_id == report_id,
            RdReportGenJob.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(RdReportGenJob.created_at.desc())
        .limit(1)
    )
    return result.scalars().first()


async def build_options(
    session: AsyncSession,
    *,
    project_id: uuid.UUID,
    stage: str,
    deliverable_type: str,
    deliverable_id: uuid.UUID | None = None,
) -> RdStageDeliverableGenerationOptions:
    """向导第 1、2 步的全部预填值：一次请求拿齐，前端不必串行取数。"""
    project = await _load_project(session, project_id)
    _validate_stage_type(stage, deliverable_type)

    target = await _load_deliverable(session, deliverable_id) if deliverable_id else None
    if target is not None and (
        target.project_id != project_id or target.stage != stage or target.deliverable_type != deliverable_type
    ):
        raise BadRequestException("这条交付文档与当前项目或阶段不一致，请刷新页面后重试")
    latest = target or await _latest_deliverable(session, project_id, stage, deliverable_type)

    templates, recommended_id = await _template_candidates(session, stage, deliverable_type)
    job = await _job_of_deliverable(session, latest) if latest is not None else None
    active_job = _job_brief(job) if job is not None and job.status in ACTIVE_JOB_STATUSES else None

    # 已经出过稿 → 本次算新版本；没出过稿 → 沿用原标题版本，不硬造 v1.1
    if latest is None:
        default_version = "v1.0"
    elif _has_output(latest):
        default_version = _next_version(latest.version)
    else:
        default_version = latest.version

    return RdStageDeliverableGenerationOptions(
        project_id=project.id,
        project_name=project.name,
        api_name=project.api_name,
        stage=stage,
        stage_label=stage_label(stage),
        deliverable_type=deliverable_type,
        deliverable_type_label=deliverable_type_label(deliverable_type),
        deliverable_id=latest.id if latest is not None else None,
        default_title=_default_title(project, stage, deliverable_type),
        default_version=default_version,
        default_doc_code=_default_doc_code(stage, deliverable_type),
        default_drug_name=project.name,
        templates=templates,
        recommended_template_id=recommended_id,
        existing_report_id=latest.report_id if latest is not None else None,
        active_job=active_job,
    )


async def _resolve_template(
    session: AsyncSession,
    *,
    stage: str,
    deliverable_type: str,
    template_id: uuid.UUID | None,
) -> RdDeliverableTemplate:
    """模板：显式传了就用它，否则按阶段+类型自动匹配；都给不出明确报错指向模板页。"""
    if template_id is not None:
        template = await session.get(RdDeliverableTemplate, template_id)
        if template is None or template.is_deleted:
            raise NotFoundException("交付文档模板", str(template_id))
    else:
        options, recommended_id = await _template_candidates(session, stage, deliverable_type)
        if recommended_id is None:
            raise BadRequestException(
                f"「{stage_label(stage)} · {deliverable_type_label(deliverable_type)}」还没有可用的 Word 模板。"
                "请先到「研发管理 → 交付文档模板」上传母本并启用"
            )
        template = await session.get(RdDeliverableTemplate, recommended_id)
        if template is None:
            raise BadRequestException("模板已失效，请刷新页面后重试")

    if not template.file_object_key:
        raise BadRequestException(
            f"模板「{template.name}」还没有上传 Word 文件，没法生成。请先到「交付文档模板」页给它上传母本"
        )
    return template


async def _resolve_report(
    session: AsyncSession,
    *,
    deliverable: RdStageDeliverable,
    project_id: uuid.UUID,
    stage: str,
    user_id: uuid.UUID | None,
) -> RdReport:
    """报告复用：只认这条交付文档已挂的报告，否则新建一份。

    特意不按「项目 + 阶段 + 标题」匹配：报告模块里可能有手工建的同名报告，
    按标题复用会把无关报告挂过来，两边的版本与附件从此纠缠。
    """
    if deliverable.report_id:
        report = await session.get(RdReport, deliverable.report_id)
        if report is not None and not report.is_deleted:
            return report

    report = RdReport(
        project_id=project_id,
        title=deliverable.title,
        report_type="stage",
        stage=stage,
        status="in_progress",
        version=deliverable.version,
        author_id=user_id,
        created_by=user_id,
        updated_by=user_id,
    )
    session.add(report)
    await session.flush()
    return report


async def generate(
    session: AsyncSession,
    payload: RdStageDeliverableGenerateRequest,
    user_id: uuid.UUID | None,
) -> RdStageDeliverableGenerateResult:
    """一次编排：交付文档 → 报告 → 生成任务。返回给前端的只有三个 id 和状态。"""
    project = await _load_project(session, payload.project_id)
    _validate_stage_type(payload.stage, payload.deliverable_type)

    template = await _resolve_template(
        session,
        stage=payload.stage,
        deliverable_type=payload.deliverable_type,
        template_id=payload.template_id,
    )

    # ── 交付文档：显式传入就复用；否则按「同阶段同类型」找最新一条 ──
    deliverable = (
        await _load_deliverable(session, payload.deliverable_id)
        if payload.deliverable_id
        else await _latest_deliverable(session, payload.project_id, payload.stage, payload.deliverable_type)
    )
    if deliverable is not None and (
        deliverable.project_id != payload.project_id
        or deliverable.stage != payload.stage
        or deliverable.deliverable_type != payload.deliverable_type
    ):
        raise BadRequestException("这条交付文档与当前项目或阶段不一致，请刷新页面后重试")

    # 幂等要放在「新建版本行」之前：连点两次时先命中在跑的任务直接返回，
    # 否则每次点击都会先落一条空版本行，再挂回同一个任务，留下无用空行。
    if deliverable is not None and deliverable.report_id:
        running = await _active_job_of_report(session, deliverable.report_id)
        if running is not None:
            if deliverable.report_gen_job_id != running.id:
                deliverable.report_gen_job_id = running.id
                deliverable.updated_by = user_id
                await session.commit()
            return RdStageDeliverableGenerateResult(
                deliverable_id=deliverable.id,
                report_id=deliverable.report_id,
                job_id=running.id,
                job_status=running.status,
                reused=True,
            )

    if deliverable is None or _has_output(deliverable):
        # 没出过稿就补建一条草稿；已出过稿则另起一条版本行，旧版本与旧附件都留着
        title = (payload.title or "").strip() or _default_title(project, payload.stage, payload.deliverable_type)
        version = (payload.version or "").strip() or (
            _next_version(deliverable.version) if deliverable is not None else "v1.0"
        )
        deliverable = RdStageDeliverable(
            project_id=payload.project_id,
            stage=payload.stage,
            deliverable_type=payload.deliverable_type,
            title=title,
            status="in_progress",
            version=version,
            owner_id=user_id,
            created_by=user_id,
            updated_by=user_id,
        )
        session.add(deliverable)
        await session.flush()
    else:
        if (payload.title or "").strip():
            deliverable.title = (payload.title or "").strip()
        deliverable.status = "in_progress"
        deliverable.updated_by = user_id
        await session.flush()

    report = await _resolve_report(
        session,
        deliverable=deliverable,
        project_id=payload.project_id,
        stage=payload.stage,
        user_id=user_id,
    )

    # 并发兜底：两个请求同时走到这里时，create_job 会返回同一个在跑的任务
    active = await _active_job_of_report(session, report.id)
    if active is not None:
        deliverable.report_id = report.id
        deliverable.report_gen_job_id = active.id
        deliverable.updated_by = user_id
        await session.commit()
        return RdStageDeliverableGenerateResult(
            deliverable_id=deliverable.id,
            report_id=report.id,
            job_id=active.id,
            job_status=active.status,
            reused=True,
        )

    previous_job_id = deliverable.report_gen_job_id
    job_data = await create_report_gen_job(
        session,
        ReportGenJobCreateRequest(
            report_id=report.id,
            project_id=payload.project_id,
            deliverable_template_id=template.id,
            doc_code=(payload.doc_code or "").strip() or _default_doc_code(payload.stage, payload.deliverable_type),
            drug_name=(payload.drug_name or "").strip() or None,
            supplement_text=(payload.supplement_text or "").strip() or None,
        ),
        user_id,
    )

    deliverable.report_id = report.id
    deliverable.report_gen_job_id = job_data.id
    deliverable.updated_by = user_id
    await session.commit()

    logger.info(
        "stage deliverable generation created",
        extra={
            "deliverable_id": str(deliverable.id),
            "report_id": str(report.id),
            "job_id": str(job_data.id),
            "template_id": str(template.id),
        },
    )
    return RdStageDeliverableGenerateResult(
        deliverable_id=deliverable.id,
        report_id=report.id,
        job_id=job_data.id,
        job_status=job_data.status,
        # create_job 内部也会复用同报告的在跑任务（并发窗口），此时对用户而言仍是「复用」
        reused=previous_job_id == job_data.id,
    )


async def get_status(session: AsyncSession, deliverable_id: uuid.UUID) -> RdStageDeliverableGenerationStatus:
    """向导第 3 步轮询：一条交付文档 + 它最近的任务。"""
    deliverable = await _load_deliverable(session, deliverable_id)
    job = await _job_of_deliverable(session, deliverable)
    if job is None:
        return RdStageDeliverableGenerationStatus(
            deliverable_id=deliverable.id,
            report_id=deliverable.report_id,
            status="idle",
            progress=0,
            current_step="还没开始生成",
            document_file_name=deliverable.file_name,
            document_ready=bool(deliverable.file_name),
        )

    return RdStageDeliverableGenerationStatus(
        deliverable_id=deliverable.id,
        report_id=deliverable.report_id or job.report_id,
        job_id=job.id,
        status=job.status,
        progress=job.progress,
        current_step=job.current_step,
        error_message=job.error_message,
        slot_total=job.slot_total,
        slot_filled=job.slot_filled,
        slot_gap=job.slot_gap,
        document_file_name=job.document_file_name or deliverable.file_name,
        document_ready=bool(job.document_object_key) or bool(deliverable.file_name),
        comparison_ready=bool(job.comparison_object_key),
        updated_at=job.updated_at,
    )


async def list_report_links(
    session: AsyncSession, report_ids: list[uuid.UUID]
) -> list[RdStageDeliverableReportLink]:
    """报告 → 来源交付文档：同一报告有多条交付文档时取最新一条。"""
    if not report_ids:
        return []
    result = await session.execute(
        select(RdStageDeliverable)
        .where(
            RdStageDeliverable.is_deleted.is_(False),
            RdStageDeliverable.report_id.in_(report_ids),
        )
        .order_by(RdStageDeliverable.created_at.desc())
    )
    seen: set[uuid.UUID] = set()
    links: list[RdStageDeliverableReportLink] = []
    for row in result.scalars().all():
        if row.report_id is None or row.report_id in seen:
            continue
        seen.add(row.report_id)
        links.append(
            RdStageDeliverableReportLink(
                report_id=row.report_id,
                deliverable_id=row.id,
                project_id=row.project_id,
                stage=row.stage,
                stage_label=stage_label(row.stage),
                deliverable_type=row.deliverable_type,
                deliverable_type_label=deliverable_type_label(row.deliverable_type),
                version=row.version,
            )
        )
    return links


async def attach_generation_briefs(session: AsyncSession, items: list[RdStageDeliverable]) -> None:
    """给列表批量挂上「生成中 62%」徽标数据；一次查询，避免 N+1。"""
    job_ids = [item.report_gen_job_id for item in items if item.report_gen_job_id]
    if not job_ids:
        return
    result = await session.execute(
        select(RdReportGenJob).where(
            RdReportGenJob.is_deleted.is_(False),
            RdReportGenJob.id.in_(job_ids),
        )
    )
    jobs = {job.id: job for job in result.scalars().all()}
    for item in items:
        if not item.report_gen_job_id:
            continue
        brief = _job_brief(jobs.get(item.report_gen_job_id))
        if brief is not None:
            setattr(item, "generation", brief)


async def sync_job_result(session: AsyncSession, job: RdReportGenJob) -> None:
    """任务出稿后把 docx 落进交付文档附件并回写。

    只在任务 completed 时调用。文件读写失败只记日志——附件没复制成功不能让
    「已经生成好的报告」被判失败，用户仍能从报告详情下载。

    数据库异常不在这里吞掉：吞了会让 session 停在失效事务上，调用方后面的
    commit 依旧会炸，反而把「为什么失败」掩盖成一次莫名的事务错误。
    """
    if job.status != "completed" or not job.document_object_key:
        return

    result = await session.execute(
        select(RdStageDeliverable).where(
            RdStageDeliverable.is_deleted.is_(False),
            RdStageDeliverable.report_gen_job_id == job.id,
        )
    )
    deliverable = result.scalars().first()
    if deliverable is None:
        return

    try:
        data = artifact_store.load_bytes(str(job.document_object_key))
        if data is None:
            logger.warning(
                "stage deliverable sync skipped: artifact missing",
                extra={"job_id": str(job.id), "deliverable_id": str(deliverable.id)},
            )
            return
        file_name = deliverable_files.safe_file_name(job.document_file_name or f"{deliverable.title}.docx")
        file_size = deliverable_files.save_deliverable_bytes(deliverable.id, file_name, data)
    except Exception:  # noqa: BLE001 - 回写是增益项，拷文件失败不能影响任务终态
        logger.exception("stage deliverable artifact copy failed", extra={"job_id": str(job.id)})
        return

    deliverable.file_name = file_name
    deliverable.file_size = file_size
    deliverable.file_url = deliverable_files.deliverable_download_url(deliverable.id)
    # 状态停在「编写中」：出稿不等于定稿，等人工核对后再置 completed/approved
    if deliverable.status == "draft":
        deliverable.status = "in_progress"
    await session.flush()
    logger.info(
        "stage deliverable artifact synced",
        extra={"job_id": str(job.id), "deliverable_id": str(deliverable.id), "bytes": file_size},
    )
