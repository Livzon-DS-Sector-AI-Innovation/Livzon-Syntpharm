"""PPT 配音视频业务编排。

API 层只做参数校验与响应组装，所有跨表/跨存储的动作落在这里：
项目创建（解析 PPT + 讲稿切分）、讲稿保存、试听、入队渲染、版本与复用记录查询。
真正的渲染在 `worker.py` 里跑（独立容器），本模块不调用 ffmpeg。
"""

import asyncio
import logging
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.modules.agent import ai_config, editor, parser, queue, rewrite, script_ai, source_replace, tts
from app.modules.agent.cache import (
    Manifest,
    body_input_key,
    normalize_script,
    script_key,
    sha256_bytes,
    slide_input_key,
    voice_key,
)
from app.modules.agent.cache import (
    audio_key as build_audio_key,
)
from app.modules.agent.config import (
    DEFAULTS,
    MAX_SCRIPT_CHARS,
    MODULE_CODE,
    SCRIPT_GUIDE_MAX_CHARS,
    PptVideoSettings,
    load_settings,
)
from app.modules.agent.models import (
    PROJECT_STATUS_DRAFT,
    PROJECT_STATUS_RENDERING,
    REWRITE_MODE_SOURCE_REPLACE,
    SCRIPT_AI_STATUS_DISABLED,
    SCRIPT_AI_STATUS_DONE,
    SCRIPT_AI_STATUS_FAILED,
    SCRIPT_AI_STATUS_PARTIAL,
    SCRIPT_AI_STATUS_QUEUED,
    SCRIPT_AI_STATUS_RUNNING,
    SCRIPT_SOURCE_MANUAL,
    SCRIPT_SOURCE_UPLOAD,
    PptVideoJob,
    PptVideoProject,
    PptVideoSlide,
    PptVideoVersion,
)
from app.modules.agent.schemas import (
    EditableShapeItem,
    EditableShapeList,
    JobState,
    ManifestResponse,
    ManifestSlideItem,
    ProjectDetail,
    ProjectSummary,
    ReuseSummary,
    RevisionItem,
    ScriptAiState,
    ScriptRewriteResult,
    ScriptRuntime,
    SlideEditResult,
    SlideItem,
    SourceApplyResult,
    SourceDiffSummary,
    VersionItem,
)
from app.modules.agent.voices import is_voice_in_language, list_voices

logger = logging.getLogger(__name__)

BUCKET_MODULE = MODULE_CODE

GUIDE_MAX_CHARS = SCRIPT_GUIDE_MAX_CHARS


class ServiceError(ValueError):
    """业务校验失败，message 直接回给前端（HTTP 400）。"""


class NotFoundError(LookupError):
    """资源不存在（HTTP 404）。"""


# ── 对象路径（全部服务端生成，禁止拼接用户输入） ────────────────────────────


def source_object_key(project_id: uuid.UUID, version: int = 1) -> str:
    """源 PPT 按版本存，改坏了可以回上一版。"""
    return f"ppt-video/{project_id}/source-v{version}.pptx"


def slide_image_key(project_id: uuid.UUID, slide_uid: uuid.UUID) -> str:
    """页图按稳定身份存。用页码的话，插页会让新页覆盖旧页的图。"""
    return f"ppt-video/{project_id}/slides/{slide_uid}.png"


def audio_object_key(audio_fingerprint: str) -> str:
    """旁白按内容寻址存：不同项目同一页讲稿可共用一份音频。"""
    return f"ppt-video/audio/{audio_fingerprint}.wav"


def segment_object_key(segment_fingerprint: str) -> str:
    return f"ppt-video/segments/{segment_fingerprint}.mp4"


def video_object_key(project_id: uuid.UUID, version_no: int) -> str:
    return f"ppt-video/{project_id}/versions/v{version_no:04d}.mp4"


def image_url(project_id: uuid.UUID, slide_no: int, version_token: str | None = None) -> str:
    """页图地址带内容指纹，换源重排后同一页码的图不会被浏览器缓存顶住。"""
    base = f"/api/v1/agent/ppt-videos/{project_id}/slides/{slide_no}/image"
    return f"{base}?v={version_token[:12]}" if version_token else base


def audio_url(project_id: uuid.UUID, slide_no: int, version_token: str | None = None) -> str:
    base = f"/api/v1/agent/ppt-videos/{project_id}/slides/{slide_no}/audio"
    return f"{base}?v={version_token[:12]}" if version_token else base


def download_url(version_id: uuid.UUID) -> str:
    return f"/api/v1/agent/ppt-videos/versions/{version_id}/file"


# ── 参数解析 ────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class EffectiveVoice:
    language: str
    voice_id: str
    speed: float
    script: str
    script_sha256: str
    voice_fingerprint: str
    input_key: str


def resolve_effective(
    slide: PptVideoSlide,
    project: PptVideoProject,
    engine_name: str,
    engine_version: str,
) -> EffectiveVoice:
    """页级覆盖 > 项目默认。音色与语言不匹配时回落到该语言默认音色。"""
    language = slide.language or project.default_language or DEFAULTS.default_language
    voice_id = slide.voice_id or project.default_voice_id
    speed = slide.speed or project.speed or DEFAULTS.default_speed
    if not is_voice_in_language(voice_id, language):
        fallback = DEFAULTS.default_voice_zh if language == "zh" else DEFAULTS.default_voice_en
        logger.warning("voice %s 不属于语言 %s，回落默认 %s", voice_id, language, fallback)
        voice_id = fallback
    script = normalize_script(slide.script_text or "")
    script_sha256 = script_key(script, language)
    fingerprint = voice_key(language, voice_id, speed, engine_name, engine_version)
    return EffectiveVoice(
        language=language,
        voice_id=voice_id,
        speed=speed,
        script=script,
        script_sha256=script_sha256,
        voice_fingerprint=fingerprint,
        input_key=slide_input_key(slide.slide_no, script_sha256, fingerprint),
    )


def compute_body_input_key(
    slides: list[PptVideoSlide],
    project: PptVideoProject,
    engine_name: str,
    engine_version: str,
) -> str:
    """正文输入签名（第 2 页起）。空讲稿的页不参与，避免未填页阻塞判断。"""
    keys = [
        resolve_effective(slide, project, engine_name, engine_version).input_key
        for slide in sorted(slides, key=lambda item: item.slide_no)
        if slide.slide_no > 1
    ]
    return body_input_key(keys)


def current_engine(settings: PptVideoSettings) -> tuple[str, str]:
    name = (settings.tts_engine or DEFAULTS.tts_engine).lower()
    return name, tts.get_engine(name).version()


# ── 项目 ────────────────────────────────────────────────────────────────────


async def create_project(
    session: AsyncSession,
    *,
    file_bytes: bytes,
    filename: str,
    name: str | None,
    script_bytes: bytes | None,
    script_filename: str | None,
    default_language: str,
    default_voice_id: str | None,
    speed: float,
    created_by: uuid.UUID | None,
) -> PptVideoProject:
    """上传 PPT（+ 可选讲稿）→ 解析页序 → 建项目与逐页记录。"""
    suffix = Path(filename).suffix.lower()
    if suffix not in (".ppt", ".pptx"):
        raise ServiceError("文件格式不支持：仅支持 .ppt 或 .pptx")
    if not file_bytes:
        raise ServiceError("上传的 PPT 文件为空")
    if default_language not in ("zh", "en"):
        raise ServiceError("语言仅支持 zh 或 en")
    voice_id = default_voice_id or DEFAULTS.default_voice_zh
    if not is_voice_in_language(voice_id, default_language):
        raise ServiceError("默认音色与默认语言不匹配，请重新选择")
    if not 0.5 <= speed <= 2.0:
        raise ServiceError("语速需在 0.5~2.0 之间")

    project_id = uuid.uuid4()
    work_dir = Path(tempfile.mkdtemp(prefix=f"pptvideo-{project_id.hex[:8]}-"))
    try:
        raw_path = work_dir / f"source{suffix}"
        raw_path.write_bytes(file_bytes)
        pptx_path = parser.convert_to_pptx(raw_path, work_dir)
        parsed = parser.parse_pptx(pptx_path)
        if len(parsed) > DEFAULTS.max_slides:
            raise ServiceError(f"PPT 页数过大（{len(parsed)} 页），单次最多 {DEFAULTS.max_slides} 页")

        script_result: parser.ScriptParseResult | None = None
        if script_bytes:
            script_path = work_dir / f"script{Path(script_filename or 'script.txt').suffix or '.txt'}"
            script_path.write_bytes(script_bytes)
            try:
                script_text = parser.read_script_file(script_path)
            except parser.ParserError as exc:
                raise ServiceError(str(exc)) from exc
            script_result = parser.split_script(script_text, len(parsed))

        pptx_bytes = pptx_path.read_bytes()
        storage.upload_object(
            BUCKET_MODULE,
            source_object_key(project_id),
            pptx_bytes,
            len(pptx_bytes),
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

        project = PptVideoProject(
            id=project_id,
            name=(name or Path(filename).stem)[:255],
            source_filename=filename[:255],
            source_object_key=source_object_key(project_id),
            source_sha256=sha256_bytes(pptx_bytes),
            slide_count=len(parsed),
            default_language=default_language,
            default_voice_id=voice_id,
            speed=speed,
            status=PROJECT_STATUS_DRAFT,
            created_by=created_by,
            updated_by=created_by,
        )
        session.add(project)
        for item in parsed:
            script = ""
            if script_result is not None:
                script = script_result.slides.get(item.slide_no, "")
            script = script[:MAX_SCRIPT_CHARS]
            session.add(
                PptVideoSlide(
                    id=uuid.uuid4(),
                    project_id=project_id,
                    slide_uid=uuid.uuid4(),
                    slide_no=item.slide_no,
                    source_index=item.slide_no,
                    script_text=script,
                    script_source=SCRIPT_SOURCE_UPLOAD if not script_ai.is_blank_script(script) else "",
                    page_text=(item.text or "")[:5000] or None,
                    page_notes=(item.notes or "")[:5000] or None,
                    layout=item.layout,
                    page_fingerprint=item.fingerprint,
                    created_by=created_by,
                    updated_by=created_by,
                )
            )
        await session.flush()
        return project
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


async def start_script_ai(
    session: AsyncSession,
    project_id: uuid.UUID,
    settings: PptVideoSettings,
    *,
    force: bool = False,
) -> ScriptAiState:
    """发起 AI 讲稿初稿生成（幂等）。

    - 任务已在排队/运行中 → 直接返回当前状态，不重复提交；
    - 功能关闭 → 置 disabled，不提交；
    - 没有待生成页（讲稿都已有，或全部是无文字页）→ 直接置 done；
    - 其余情况先置 queued 并**提交事务**，再交给 `core.jobs` 后台执行：
      后台任务用独立会话读库，不提交就查不到刚建的项目与空页。

    Args:
        force: 工作台手动重试时传 True。后台任务若因服务重启停在 running，
            状态永远不会自己变化，此时只有强制重发才能继续；重复执行也不会
            覆盖已有讲稿（写入是条件 UPDATE），代价只是多花一次模型调用。
    """
    project = await get_project(session, project_id)
    slides = await list_slides(session, project_id)
    state = script_ai_state(project, slides)

    if state.status in (SCRIPT_AI_STATUS_QUEUED, SCRIPT_AI_STATUS_RUNNING) and not force:
        return state

    if not settings.script_ai_enabled:
        project.script_ai_status = SCRIPT_AI_STATUS_DISABLED
        project.script_ai_progress = 0
        project.script_ai_error = None
        await session.flush()
        return script_ai_state(project, slides)

    if state.pending == 0:
        project.script_ai_status = SCRIPT_AI_STATUS_DONE
        project.script_ai_progress = 100
        project.script_ai_error = None
        await session.flush()
        return script_ai_state(project, slides)

    project.script_ai_status = SCRIPT_AI_STATUS_QUEUED
    project.script_ai_progress = 0
    project.script_ai_error = None
    await session.flush()
    await session.commit()

    await script_ai.submit(project_id)
    return script_ai_state(project, slides)


async def get_project(session: AsyncSession, project_id: uuid.UUID) -> PptVideoProject:
    project = await session.scalar(
        select(PptVideoProject).where(PptVideoProject.id == project_id, PptVideoProject.is_deleted.is_(False))
    )
    if project is None:
        raise NotFoundError("项目不存在或已删除")
    return project


async def list_slides(session: AsyncSession, project_id: uuid.UUID) -> list[PptVideoSlide]:
    slides = await session.scalars(
        select(PptVideoSlide)
        .where(PptVideoSlide.project_id == project_id, PptVideoSlide.is_deleted.is_(False))
        .order_by(PptVideoSlide.slide_no)
    )
    return list(slides)


async def get_slide(session: AsyncSession, project_id: uuid.UUID, slide_no: int) -> PptVideoSlide:
    slide = await session.scalar(
        select(PptVideoSlide).where(
            PptVideoSlide.project_id == project_id,
            PptVideoSlide.slide_no == slide_no,
            PptVideoSlide.is_deleted.is_(False),
        )
    )
    if slide is None:
        raise NotFoundError(f"第 {slide_no} 页不存在")
    return slide


async def get_slide_by_uid(session: AsyncSession, project_id: uuid.UUID, slide_uid: str) -> PptVideoSlide:
    """按稳定身份取页；写讲稿、试听、页级编辑都用它，避免页码变动导致改错页。"""
    try:
        parsed_uid = uuid.UUID(str(slide_uid))
    except (TypeError, ValueError) as exc:
        raise NotFoundError("页面标识不正确") from exc
    slide = await session.scalar(
        select(PptVideoSlide).where(
            PptVideoSlide.project_id == project_id,
            PptVideoSlide.slide_uid == parsed_uid,
            PptVideoSlide.is_deleted.is_(False),
        )
    )
    if slide is None:
        raise NotFoundError("页面不存在或已被删除")
    return slide


async def list_versions(session: AsyncSession, project_id: uuid.UUID) -> list[PptVideoVersion]:
    versions = await session.scalars(
        select(PptVideoVersion)
        .where(PptVideoVersion.project_id == project_id, PptVideoVersion.is_deleted.is_(False))
        .order_by(PptVideoVersion.version_no.desc())
    )
    return list(versions)


def version_item(version: PptVideoVersion) -> VersionItem:
    manifest = version.manifest or {}
    reuse = ReuseSummary.model_validate(manifest.get("reuse", {}))
    return VersionItem(
        id=version.id,
        version_no=version.version_no,
        file_name=version.file_name,
        file_size=version.file_size,
        duration_ms=version.duration_ms,
        file_sha256=version.file_sha256,
        head_key=version.head_key,
        body_key=version.body_key,
        reuse=reuse,
        download_url=download_url(version.id),
        created_at=version.created_at,
    )


def slide_item(slide: PptVideoSlide, project_id: uuid.UUID) -> SlideItem:
    return SlideItem(
        slide_no=slide.slide_no,
        slide_uid=slide.slide_uid,
        script_text=slide.script_text or "",
        script_source=slide.script_source or "",
        script_stale=bool(slide.script_stale),
        has_page_text=script_ai.is_generatable(slide.page_text, slide.page_notes),
        language=slide.language,
        voice_id=slide.voice_id,
        speed=slide.speed,
        page_text=slide.page_text,
        page_notes=slide.page_notes,
        image_url=image_url(project_id, slide.slide_no, slide.image_sha256) if slide.image_object_key else None,
        audio_url=audio_url(project_id, slide.slide_no, slide.audio_sha256) if slide.audio_object_key else None,
        audio_sha256=slide.audio_sha256,
        duration_ms=slide.duration_ms or 0,
        has_audio=bool(slide.audio_object_key),
    )


def script_ai_state(project: PptVideoProject, slides: list[PptVideoSlide]) -> ScriptAiState:
    """AI 讲稿初稿状态：进度来自项目列，计数由当前 slides 现算。"""
    total = 0
    done = 0
    pending = 0
    skipped = 0
    for slide in slides:
        has_text = script_ai.is_generatable(slide.page_text, slide.page_notes)
        blank = script_ai.is_blank_script(slide.script_text)
        if has_text:
            total += 1
            if blank:
                pending += 1
            else:
                done += 1
        elif blank:
            skipped += 1

    status = project.script_ai_status or "idle"
    finished_with_gap = status in (SCRIPT_AI_STATUS_PARTIAL, SCRIPT_AI_STATUS_FAILED)
    return ScriptAiState(
        status=status,
        error=project.script_ai_error,
        progress=project.script_ai_progress or 0,
        total=total,
        done=done,
        pending=pending,
        skipped=skipped,
        failed=pending if finished_with_gap else 0,
    )


def job_state(job: PptVideoJob | None) -> JobState | None:
    if job is None:
        return None
    return JobState(
        job_id=job.id,
        status=job.status,
        stage=job.stage,
        progress=job.progress or 0,
        attempts=job.attempts or 0,
        error_message=job.error_message,
        version_id=job.version_id,
        started_at=job.started_at,
        finished_at=job.finished_at,
    )


async def script_runtime_state(
    session: AsyncSession,
    project: PptVideoProject,
    settings: PptVideoSettings,
    user_id: uuid.UUID | None,
) -> ScriptRuntime:
    """页面回显用的「现在到底用哪个模型、遵守什么风格」。

    解析失败不抛错：页面详情不该因为 Key 配错了整页打不开，
    失败时用空模型名 + env 来源表示「待配置」。
    """
    global_config_id, global_guide = await ai_config.read_global_settings(session)
    try:
        model = await ai_config.resolve(session, project, user_id)
        model_name = model.model_name
        provider = model.provider
        source = model.source
        config_id = model.config_id
    except Exception:  # noqa: BLE001 - 回显失败只降级，不影响详情
        logger.warning("生效模型解析失败，详情页降级展示: project=%s", project.id)
        model_name, provider, source, config_id = "", "", "env", None

    guide = await ai_config.resolve_guide(session, project)
    return ScriptRuntime(
        model_name=model_name,
        provider=provider,
        source=source,
        config_id=uuid.UUID(str(config_id)) if config_id else None,
        project_config_id=project.llm_config_id,
        global_config_id=uuid.UUID(global_config_id) if global_config_id else None,
        global_guide=global_guide,
        project_guide=guide.project_guide,
        effective_guide=guide.effective,
        guide_max_chars=settings.script_guide_max_chars,
        highlight_enabled=settings.highlight_enabled,
    )


async def get_detail(
    session: AsyncSession,
    project_id: uuid.UUID,
    settings: PptVideoSettings | None = None,
    user_id: uuid.UUID | None = None,
) -> ProjectDetail:
    settings = settings or DEFAULTS
    project = await get_project(session, project_id)
    slides = await list_slides(session, project_id)
    versions = await list_versions(session, project_id)
    job = await queue.get_latest(session, project_id)
    engine_name, engine_version = current_engine(settings)
    current_body = compute_body_input_key(slides, project, engine_name, engine_version)
    return ProjectDetail(
        id=project.id,
        name=project.name,
        source_filename=project.source_filename,
        slide_count=project.slide_count,
        default_language=project.default_language,
        default_voice_id=project.default_voice_id,
        speed=project.speed,
        status=project.status,
        head_key=project.head_key,
        body_key=project.body_key,
        current_body_key=current_body,
        body_stale=bool(project.body_input_key) and project.body_input_key != current_body,
        slides=[slide_item(slide, project_id) for slide in slides],
        versions=[version_item(version) for version in versions],
        latest_job=job_state(job),
        script_ai=script_ai_state(project, slides),
        script_runtime=await script_runtime_state(session, project, settings, user_id),
        source_version=project.source_version or 1,
        script_guide=project.script_guide or "",
        llm_config_id=project.llm_config_id,
        updated_at=project.updated_at,
    )


async def list_projects(
    session: AsyncSession,
    *,
    keyword: str | None,
    status: str | None,
    language: str | None = None,
    page: int,
    page_size: int,
) -> tuple[list[ProjectSummary], int]:
    conditions: list[ColumnElement[bool]] = [PptVideoProject.is_deleted.is_(False)]
    if keyword:
        conditions.append(PptVideoProject.name.ilike(f"%{keyword}%"))
    if status:
        conditions.append(PptVideoProject.status == status)
    if language:
        conditions.append(PptVideoProject.default_language == language)

    total = await session.scalar(select(func.count()).select_from(PptVideoProject).where(*conditions)) or 0
    rows = (
        (
            await session.execute(
                select(PptVideoProject)
                .where(*conditions)
                .order_by(PptVideoProject.updated_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )

    items: list[ProjectSummary] = []
    for project in rows:
        version_count = await session.scalar(
            select(func.count())
            .select_from(PptVideoVersion)
            .where(PptVideoVersion.project_id == project.id, PptVideoVersion.is_deleted.is_(False))
        )
        latest = await session.scalar(
            select(PptVideoVersion)
            .where(PptVideoVersion.project_id == project.id, PptVideoVersion.is_deleted.is_(False))
            .order_by(PptVideoVersion.version_no.desc())
            .limit(1)
        )
        items.append(
            ProjectSummary(
                id=project.id,
                name=project.name,
                source_filename=project.source_filename,
                slide_count=project.slide_count,
                default_language=project.default_language,
                default_voice_id=project.default_voice_id,
                speed=project.speed,
                status=project.status,
                version_count=version_count or 0,
                latest_version_id=latest.id if latest else None,
                latest_error=project.last_error,
                thumbnail_url=image_url(project.id, 1),
                updated_at=project.updated_at,
            )
        )
    return items, int(total)


async def update_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    *,
    name: str | None,
    default_language: str | None,
    default_voice_id: str | None,
    speed: float | None,
    updated_by: uuid.UUID | None,
) -> PptVideoProject:
    project = await get_project(session, project_id)
    if name is not None:
        project.name = name
    language = default_language or project.default_language
    if default_language is not None:
        if default_language not in ("zh", "en"):
            raise ServiceError("语言仅支持 zh 或 en")
        project.default_language = default_language
    if default_voice_id is not None:
        if not is_voice_in_language(default_voice_id, language):
            raise ServiceError("默认音色与默认语言不匹配，请重新选择")
        project.default_voice_id = default_voice_id
    elif default_language is not None:
        project.default_voice_id = DEFAULTS.default_voice_zh if language == "zh" else DEFAULTS.default_voice_en
    if speed is not None:
        if not 0.5 <= speed <= 2.0:
            raise ServiceError("语速需在 0.5~2.0 之间")
        project.speed = speed
    project.updated_by = updated_by
    await session.flush()
    return project


async def update_project_ai(
    session: AsyncSession,
    project_id: uuid.UUID,
    *,
    llm_config_id: str | None,
    script_guide: str | None,
    clear_config: bool,
    clear_guide: bool,
    updated_by: uuid.UUID | None,
) -> PptVideoProject:
    """项目级 AI 设置：模型覆盖与风格指南。

    `llm_config_id` 传空字符串表示清除覆盖（回到全局默认），传 None 表示不修改。
    """
    project = await get_project(session, project_id)
    if clear_config:
        project.llm_config_id = None
    elif llm_config_id is not None:
        if llm_config_id:
            try:
                project.llm_config_id = uuid.UUID(llm_config_id)
            except (TypeError, ValueError) as exc:
                raise ServiceError("模型配置标识不正确") from exc
        else:
            project.llm_config_id = None
    if clear_guide:
        project.script_guide = None
    elif script_guide is not None:
        guide = script_guide.strip()
        project.script_guide = guide[:GUIDE_MAX_CHARS] or None
    project.updated_by = updated_by
    await session.flush()
    return project


async def update_slide(
    session: AsyncSession,
    project_id: uuid.UUID,
    slide_uid: str,
    *,
    script_text: str | None,
    language: str | None,
    voice_id: str | None,
    speed: float | None,
    clear_language: bool,
    clear_voice: bool,
    clear_speed: bool,
    updated_by: uuid.UUID | None,
) -> PptVideoSlide:
    project = await get_project(session, project_id)
    slide = await get_slide_by_uid(session, project_id, slide_uid)

    if script_text is not None:
        if len(script_text) > MAX_SCRIPT_CHARS:
            raise ServiceError(f"单页讲稿不能超过 {MAX_SCRIPT_CHARS} 字")
        slide.script_text = script_text
        slide.script_stale = False
        # 用户手改即视为自有内容：清空来源，避免后续被标成「AI 初稿」
        slide.script_source = "" if script_ai.is_blank_script(script_text) else SCRIPT_SOURCE_MANUAL
    if language is not None:
        if language not in ("zh", "en"):
            raise ServiceError("语言仅支持 zh 或 en")
        slide.language = language
        # 语言变了但音色没跟着变 → 清掉音色覆盖，回落项目默认
        effective_language = language
        if (slide.voice_id or project.default_voice_id) and not is_voice_in_language(
            slide.voice_id or project.default_voice_id, effective_language
        ):
            slide.voice_id = None
    if voice_id is not None:
        effective_language = language or slide.language or project.default_language
        if not is_voice_in_language(voice_id, effective_language):
            raise ServiceError("音色与当前页语言不匹配，请重新选择")
        slide.voice_id = voice_id
    if speed is not None:
        if not 0.5 <= speed <= 2.0:
            raise ServiceError("语速需在 0.5~2.0 之间")
        slide.speed = speed
    if clear_language:
        slide.language = None
    if clear_voice:
        slide.voice_id = None
    if clear_speed:
        slide.speed = None
    slide.updated_by = updated_by
    await session.flush()
    return slide


async def preview_slide(
    session: AsyncSession,
    project_id: uuid.UUID,
    slide_uid: str,
    settings: PptVideoSettings,
) -> tuple[int, str, int, str]:
    """单页试听：命中缓存直接返回，否则合成 wav 并落 MinIO。"""
    project = await get_project(session, project_id)
    slide = await get_slide_by_uid(session, project_id, slide_uid)

    engine_name, engine_version = current_engine(settings)
    effective = resolve_effective(slide, project, engine_name, engine_version)
    if not effective.script:
        raise ServiceError("本页讲稿为空，请先填写后再试听")

    fingerprint = build_audio_key(effective.script_sha256, effective.voice_fingerprint)
    if slide.audio_key == fingerprint and slide.audio_object_key:
        return (
            slide.slide_no,
            audio_url(project_id, slide.slide_no, slide.audio_sha256),
            slide.duration_ms or 0,
            slide.audio_sha256 or "",
        )

    work_dir = Path(tempfile.mkdtemp(prefix=f"preview-{project_id.hex[:8]}-"))
    try:
        wav_path = work_dir / "preview.wav"
        try:
            result = tts.synthesize_to_wav(
                effective.script, effective.language, effective.voice_id, effective.speed, wav_path, engine_name
            )
        except tts.TtsError as exc:
            raise ServiceError(str(exc)) from exc

        wav_bytes = wav_path.read_bytes()
        object_key = audio_object_key(fingerprint)
        storage.upload_object(BUCKET_MODULE, object_key, wav_bytes, len(wav_bytes), "audio/wav")

        slide.audio_object_key = object_key
        slide.audio_key = fingerprint
        slide.audio_sha256 = result.sha256
        slide.duration_ms = result.duration_ms
        await session.flush()
        return slide.slide_no, audio_url(project_id, slide.slide_no, result.sha256), result.duration_ms, result.sha256
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


async def request_render(
    session: AsyncSession,
    project_id: uuid.UUID,
    settings: PptVideoSettings,
    requested_by_name: str | None,
) -> PptVideoJob:
    """入队渲染任务；已排队时复用同一条任务（幂等）。"""
    project = await get_project(session, project_id)
    slides = await list_slides(session, project_id)
    if not slides:
        raise ServiceError("项目没有可用页面")
    empty_pages = [str(slide.slide_no) for slide in slides if not normalize_script(slide.script_text or "")]
    if empty_pages:
        raise ServiceError("以下页面还没有讲稿：" + "、".join(empty_pages))

    job = await queue.enqueue(session, project_id, requested_by_name, settings.max_attempts)
    project.status = PROJECT_STATUS_RENDERING
    await session.flush()
    return job


async def delete_project(session: AsyncSession, project_id: uuid.UUID, updated_by: uuid.UUID | None) -> None:
    project = await get_project(session, project_id)
    await queue.cancel_pending(session, project_id)
    project.is_deleted = True
    project.updated_by = updated_by
    await session.flush()


async def get_version(session: AsyncSession, version_id: uuid.UUID) -> PptVideoVersion:
    version = await session.scalar(
        select(PptVideoVersion).where(PptVideoVersion.id == version_id, PptVideoVersion.is_deleted.is_(False))
    )
    if version is None:
        raise NotFoundError("版本不存在或已删除")
    return version


def version_manifest(version: PptVideoVersion) -> ManifestResponse:
    manifest: dict[str, Any] = version.manifest or {}
    return ManifestResponse(
        version_id=version.id,
        head_key=version.head_key,
        body_key=version.body_key,
        encoder_key=str(manifest.get("encoder_key", "")),
        total_duration_ms=int(manifest.get("total_duration_ms", version.duration_ms or 0)),
        reuse=ReuseSummary.model_validate(manifest.get("reuse", {})),
        slides=[ManifestSlideItem(**item) for item in Manifest.from_dict(manifest).as_dict()["slides"]],
    )


def voice_options() -> list[dict[str, Any]]:
    return [
        {
            "voice_id": voice.voice_id,
            "language": voice.language,
            "display_name": voice.display_name,
            "gender": voice.gender,
            "license": voice.license,
            "version": voice.version,
            "source": voice.source,
        }
        for voice in list_voices()
    ]


# ── 讲稿改写 ───────────────────────────────────────────────────────────────


async def rewrite_scripts(
    session: AsyncSession,
    project_id: uuid.UUID,
    *,
    mode: str,
    slide_uids: list[str],
    instruction: str | None,
    background: bool,
    settings: PptVideoSettings,
    user_id: uuid.UUID | None,
    requested_by_name: str | None,
) -> ScriptRewriteResult:
    """四种语义共用入口：批量走后台任务，单页同步返回。

    单页同步是刻意的：编辑区点「AI 改写本页」必须就地看到结果，
    而批量改写可能跑几分钟，占住请求会被网关掐断。
    """
    project = await get_project(session, project_id)
    payload = {
        "mode": mode,
        "slide_uids": slide_uids,
        "instruction": instruction,
        "requested_by_name": requested_by_name,
    }
    if background:
        await rewrite.submit(project_id, payload, user_id)
        return ScriptRewriteResult(status="queued", total=len(slide_uids))

    result = await rewrite.run(
        session,
        project,
        rewrite.RewriteRequest(
            mode=mode,
            slide_uids=slide_uids,
            instruction=instruction,
            requested_by_name=requested_by_name,
        ),
        settings,
        user_id,
    )
    return ScriptRewriteResult.model_validate(result.to_dict())


# ── 修订记录 ───────────────────────────────────────────────────────────────


async def list_script_revisions(session: AsyncSession, project_id: uuid.UUID, limit: int = 30) -> list[RevisionItem]:
    await get_project(session, project_id)
    rows = await rewrite.list_revisions(session, project_id, limit)
    return [
        RevisionItem(
            id=row.id,
            mode=row.mode,
            instruction=row.instruction or "",
            model_name=row.model_name or "",
            provider=row.provider or "",
            status=row.status,
            progress=row.progress or 0,
            scope_count=len(row.scope or []),
            applied=bool(row.applied),
            error_message=row.error_message or "",
            requested_by_name=row.requested_by_name or "",
            source_version=row.source_version or 1,
            created_at=row.created_at,
        )
        for row in rows
    ]


async def rollback_script_revision(
    session: AsyncSession,
    project_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> int:
    """回滚一次改写，返回恢复页数。只回写 before，不删除修订记录。"""
    await get_project(session, project_id)
    try:
        restored = await rewrite.rollback_revision(session, project_id, revision_id)
    except ValueError as exc:
        raise ServiceError(str(exc)) from exc
    await session.flush()
    logger.info("讲稿回滚: project=%s revision=%s 恢复页数=%s", project_id, revision_id, restored)
    return restored


# ── 换源（重传整份 PPT） ───────────────────────────────────────────────────


def _diff_summary(diff: Any) -> SourceDiffSummary:
    return SourceDiffSummary.model_validate(source_replace.diff_payload(diff))


async def preview_source_replace(
    session: AsyncSession,
    project_id: uuid.UUID,
    file_bytes: bytes,
    filename: str,
) -> SourceDiffSummary:
    project = await get_project(session, project_id)
    try:
        prepared = await source_replace.prepare(session, project, file_bytes, filename)
    except source_replace.SourceReplaceError as exc:
        raise ServiceError(str(exc)) from exc
    return _diff_summary(prepared.diff)


async def apply_source_replace(
    session: AsyncSession,
    project_id: uuid.UUID,
    settings: PptVideoSettings,
    requested_by_name: str | None,
    user_id: uuid.UUID | None = None,
    auto_rewrite: bool = True,
) -> SourceApplyResult:
    """应用换源结果；变更页与新增页按需提交后台改写。"""
    project = await get_project(session, project_id)
    try:
        result = await source_replace.apply(session, project, requested_by_name=requested_by_name)
    except source_replace.SourceReplaceError as exc:
        raise ServiceError(str(exc)) from exc

    if auto_rewrite and result.rewrite_uids:
        await rewrite.submit(
            project_id,
            {
                "mode": REWRITE_MODE_SOURCE_REPLACE,
                "slide_uids": result.rewrite_uids,
                "requested_by_name": requested_by_name,
                "revision_id": str(result.revision_id) if result.revision_id else None,
            },
            user_id,
        )
        logger.info("换源后已提交改写任务: project=%s 页数=%s", project_id, len(result.rewrite_uids))

    return SourceApplyResult(
        revision_id=result.revision_id,
        source_version=result.source_version,
        slide_count=result.slide_count,
        rewrite_uids=[uuid.UUID(str(uid)) for uid in result.rewrite_uids],
        diff=_diff_summary(result.diff),
    )


# ── 轻量页级编辑 ───────────────────────────────────────────────────────────


async def _current_pptx_bytes(project: PptVideoProject) -> bytes:
    """取当前源 PPT（统一是 pptx）；老项目或异常内容就地转一次。"""
    data = await asyncio.to_thread(storage.get_object, BUCKET_MODULE, project.source_object_key)
    if not data:
        raise ServiceError("源 PPT 已丢失，请重新上传")
    if data[:2] == b"PK":
        return data

    work_dir = Path(tempfile.mkdtemp(prefix=f"pptvideo-edit-{project.id.hex[:8]}-"))
    try:
        raw_path = work_dir / "source.ppt"
        raw_path.write_bytes(data)
        pptx_path = await asyncio.to_thread(parser.convert_to_pptx, raw_path, work_dir)
        return pptx_path.read_bytes()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


async def list_slide_shapes(session: AsyncSession, project_id: uuid.UUID, slide_uid: str) -> EditableShapeList:
    project = await get_project(session, project_id)
    slide = await get_slide_by_uid(session, project_id, slide_uid)
    pptx_bytes = await _current_pptx_bytes(project)
    page_index = slide.source_index or slide.slide_no
    try:
        shapes = await asyncio.to_thread(editor.list_editable_shapes, pptx_bytes, page_index)
    except editor.EditError as exc:
        raise ServiceError(str(exc)) from exc
    return EditableShapeList(
        page_index=page_index,
        items=[
            EditableShapeItem(
                index=item.index,
                name=item.name,
                kind=item.kind,
                text=item.text,
                has_picture=item.has_picture,
                editable_text=item.editable_text,
            )
            for item in shapes
        ],
    )


async def edit_slide(
    session: AsyncSession,
    project_id: uuid.UUID,
    slide_uid: str,
    edit: dict[str, Any],
    requested_by_name: str | None,
    user_id: uuid.UUID | None,
) -> SlideEditResult:
    """改一个文本框 / 换一张图，产出新源版本并只重渲受影响页。"""
    project = await get_project(session, project_id)
    slide = await get_slide_by_uid(session, project_id, slide_uid)
    page_index = slide.source_index or slide.slide_no
    payload = {**edit, "page_index": page_index}

    pptx_bytes = await _current_pptx_bytes(project)
    try:
        new_bytes = await asyncio.to_thread(editor.apply_edit, pptx_bytes, payload)
    except editor.EditError as exc:
        raise ServiceError(str(exc)) from exc

    await asyncio.to_thread(
        storage.upload_object,
        BUCKET_MODULE,
        source_replace.pending_object_key(project.id, "edited.pptx"),
        new_bytes,
        len(new_bytes),
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )
    # 编辑只改画面，不自动重写讲稿：过期标记留给用户在页面上决定
    applied = await apply_source_replace(
        session,
        project_id,
        load_settings(),
        requested_by_name,
        user_id,
        auto_rewrite=False,
    )
    return SlideEditResult(
        source_version=applied.source_version,
        revision_id=applied.revision_id,
        page_index=page_index,
        rewrite_uids=[],
        diff=applied.diff,
    )
