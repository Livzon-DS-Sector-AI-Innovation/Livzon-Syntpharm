"""智能体模块 API —— PPT 配音视频。

设计约束（AGENTS.md）：
- 所有响应走 `DataResponse[具体模型]`，禁止 `response_model=dict` / `ApiResponse`；
- 业务异常用 `BadRequestException` / `NotFoundException`，由 service 抛出后再翻译；
- 渲染耗时动作不在请求内完成：`POST .../render` 只入队并返回 202，前端轮询 `/job`；
- 媒体流（页图 / 旁白 / 成片）支持 HTTP Range，浏览器播放器才能拖动进度。
"""

import logging
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import AppException, BadRequestException, ForbiddenException, NotFoundException
from app.core.llm.config import LLMConfigModel, get_config_by_id
from app.core.llm.exceptions import LLMConfigError
from app.core.response import DataResponse
from app.core.storage import delete_object, get_object_range, stat_object
from app.modules.agent import ai_config, source_replace
from app.modules.agent import config as agent_config
from app.modules.agent import queue as agent_queue
from app.modules.agent import service as agent_service
from app.modules.agent.schemas import (
    AiConfigCreateRequest,
    AiConfigItem,
    AiConfigListResponse,
    AiConfigTestRequest,
    AiConfigTestResponse,
    AiConfigUpdateRequest,
    EditableShapeList,
    GlobalAiSettingsRequest,
    JobState,
    ManifestResponse,
    MessageResult,
    PageImagesAccepted,
    PageImagesState,
    PreviewResponse,
    ProjectAiSettingsRequest,
    ProjectDetail,
    ProjectListResponse,
    ProjectUpdateRequest,
    RenderAccepted,
    RevisionListResponse,
    ScriptRewriteRequest,
    ScriptRewriteResult,
    SlideEditResult,
    SlideEditTextRequest,
    SlideItem,
    SlideRegionsResponse,
    SlideUpdateRequest,
    SourceApplyResult,
    SourceDiffSummary,
    VersionItem,
    VoiceCatalogResponse,
    VoiceOption,
)
from app.platform.identity.models import User

logger = logging.getLogger(__name__)

router = APIRouter()

#: 媒体流分块大小（1MiB）：既不让单次 read 过大，也能覆盖播放器常见预取窗口
STREAM_CHUNK_BYTES = 1024 * 1024

BUCKET = agent_service.BUCKET_MODULE

PERM_READ = "agent:ppt-video:read"
PERM_MANAGE = "agent:ppt-video:manage"


# ── 错误翻译 ────────────────────────────────────────────────────────────────

#: 499 不在 FastAPI/Starlette 的 status 常量里：客户端主动断开（nginx 也用 499 记这种请求）
CLIENT_CLOSED_REQUEST = 499


class ClientDisconnectedException(AppException):
    """客户端已断开（HTTP 499）。

    只用来打断事务：取消上传时响应没人读，但必须让 `get_db()` 走 rollback，
    否则 `create_project()` 已 flush 的项目与逐页记录会被 commit 成半成品。
    """

    def __init__(self) -> None:
        super().__init__(status_code=CLIENT_CLOSED_REQUEST, message="客户端已取消上传")


async def _raise_if_client_disconnected(request: Request) -> None:
    """解析前先看一眼连接：客户端已走就不必白跑几十秒的 LibreOffice 转换。"""
    if await request.is_disconnected():
        raise ClientDisconnectedException()


def _discard_source_object(project_id: uuid.UUID) -> None:
    """取消新建时清掉已写入对象存储的源 PPT（数据库记录由 get_db 回滚）。"""
    try:
        delete_object(BUCKET, agent_service.source_object_key(project_id))
    except Exception:
        # 清理失败不能改变「已取消」的结论，留痕给后续人工清理
        logger.warning(
            "取消新建时清理源 PPT 失败",
            extra={"project_id": str(project_id)},
            exc_info=True,
        )


@contextmanager
def _translate_errors() -> Iterator[None]:
    """service 层只关心业务语义，HTTP 语义在这里统一翻译。"""
    try:
        yield
    except agent_service.NotFoundError as exc:
        raise NotFoundException(str(exc)) from exc
    except agent_service.ServiceError as exc:
        raise BadRequestException(str(exc)) from exc
    except LLMConfigError as exc:
        raise BadRequestException(f"模型配置不可用：{exc}") from exc


# ── 媒体流 ──────────────────────────────────────────────────────────────────


def _parse_range(header: str | None, total: int) -> tuple[int, int, bool]:
    """解析 `Range: bytes=start-end`，返回 (offset, length, 是否部分响应)。"""
    if not header or total <= 0:
        return 0, max(total, 0), False
    value = header.strip()
    if not value.lower().startswith("bytes="):
        return 0, total, False
    spec = value[6:].split(",")[0].strip()
    start_raw, _, end_raw = spec.partition("-")
    try:
        if start_raw == "":
            suffix = int(end_raw)
            if suffix <= 0:
                return 0, total, False
            start = max(total - suffix, 0)
            end = total - 1
        else:
            start = int(start_raw)
            end = int(end_raw) if end_raw else total - 1
    except ValueError:
        return 0, total, False
    start = max(start, 0)
    end = min(end, total - 1)
    if start > end:
        return 0, total, False
    return start, end - start + 1, True


def _iter_object(object_key: str, offset: int, length: int) -> Iterator[bytes]:
    """按块从对象存储读取（Starlette 会把同步生成器丢进线程池，不阻塞事件循环）。"""
    position = offset
    remaining = length
    while remaining > 0:
        chunk_size = min(STREAM_CHUNK_BYTES, remaining)
        result = get_object_range(BUCKET, object_key, position, chunk_size)
        if result is None:
            logger.warning("对象在流式读取中消失", extra={"object_key": object_key})
            break
        data, _, _ = result
        if not data:
            break
        yield data
        position += len(data)
        remaining -= len(data)


def _stream_object(
    object_key: str,
    content_type: str,
    request: Request,
    file_name: str | None = None,
    cache_control: str = "private, max-age=3600",
    *,
    inline: bool = False,
) -> StreamingResponse:
    """按需流式输出对象。

    `inline=True` 时 `Content-Disposition` 用 `inline`，浏览器直接交给 `<video>` 播放；
    默认仍是 `attachment`，下载语义与老前端完全一致。Range / 206 逻辑两者共用，
    播放器拖进度不需要额外分支。
    """
    total = stat_object(BUCKET, object_key)
    if total is None or total <= 0:
        raise NotFoundException("媒体文件")
    offset, length, partial = _parse_range(request.headers.get("range"), total)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(length),
        "Cache-Control": cache_control,
    }
    if partial:
        headers["Content-Range"] = f"bytes {offset}-{offset + length - 1}/{total}"
    if file_name:
        disposition = "inline" if inline else "attachment"
        headers["Content-Disposition"] = f"{disposition}; filename*=UTF-8''{quote(file_name)}"
    return StreamingResponse(
        _iter_object(object_key, offset, length),
        status_code=206 if partial else 200,
        media_type=content_type,
        headers=headers,
    )


def _first_existing_key(*keys: str) -> str | None:
    """按优先级返回第一个存在的对象。

    新产物（JPEG 预览/缩略图）是逐步补齐的，早期项目只有 PNG 原件，
    这里逐级回退，避免升级后老项目页图直接 404。
    """
    for key in keys:
        if stat_object(BUCKET, key) is not None:
            return key
    return None


def _slide_asset_cache_control(request: Request) -> str:
    """页图缓存策略。

    地址带内容指纹（`?v=<image_sha 前 12 位>`）时内容永不变化，可以永久缓存，
    重复打开工作台就是本地命中；列表页缩略图没有指纹，只缓存 5 分钟。
    """
    if request.query_params.get("v"):
        return "private, max-age=31536000, immutable"
    return "private, max-age=300"


# ── 音色目录 ────────────────────────────────────────────────────────────────


@router.get("/voices", summary="音色目录（含语言与商用许可）")
async def list_voices(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    language: str | None = Query(None, pattern="^(zh|en)$", description="按语言过滤"),
) -> DataResponse[VoiceCatalogResponse]:
    items = [VoiceOption(**item) for item in agent_service.voice_options()]
    if language:
        items = [item for item in items if item.language == language]
    return DataResponse[VoiceCatalogResponse](data=VoiceCatalogResponse(items=items))


# ── 项目 CRUD ───────────────────────────────────────────────────────────────


@router.get("/ppt-videos", summary="配音视频项目列表")
async def list_projects(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    keyword: str | None = Query(None, description="按项目名模糊搜索"),
    status: str | None = Query(None, pattern="^(draft|rendering|ready|failed)$", description="状态筛选"),
    language: str | None = Query(None, pattern="^(zh|en)$", description="默认语言筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectListResponse]:
    items, total = await agent_service.list_projects(
        db, keyword=keyword, status=status, language=language, page=page, page_size=page_size
    )
    return DataResponse[ProjectListResponse](
        data=ProjectListResponse(items=items),
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.post("/ppt-videos", summary="新建配音视频项目（上传 PPT + 可选逐页讲稿）")
async def create_project(
    request: Request,
    file: Annotated[UploadFile, File(description="PPT 文件（.ppt / .pptx）")],
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    script_file: Annotated[UploadFile | None, File(description="可选：按页讲稿（.txt/.md/.docx）")] = None,
    name: Annotated[str | None, Form()] = None,
    default_language: Annotated[str, Form(pattern="^(zh|en)$")] = "zh",
    default_voice_id: Annotated[str | None, Form()] = None,
    speed: Annotated[float, Form(ge=0.5, le=2.0)] = 1.0,
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectDetail]:
    settings = await agent_config.load_settings()
    file_bytes = await _read_upload(file, agent_config.MAX_UPLOAD_BYTES)
    _check_ppt_magic(file.filename or "", file_bytes)
    script_bytes: bytes | None = None
    if script_file is not None and script_file.filename:
        script_bytes = await _read_upload(script_file, agent_config.MAX_UPLOAD_BYTES)

    # 客户端已断开就别再跑几十秒的转换与解析
    await _raise_if_client_disconnected(request)

    with _translate_errors():
        project = await agent_service.create_project(
            db,
            file_bytes=file_bytes,
            filename=file.filename or "presentation.pptx",
            name=name,
            script_bytes=script_bytes,
            script_filename=script_file.filename if script_file else None,
            default_language=default_language,
            default_voice_id=default_voice_id,
            speed=speed,
            created_by=current_user.id,
        )
        # 解析期间用户可能点了「停止上传」或直接关页：create_project 只 flush 未提交，
        # 这里断开就清掉已写入的源 PPT 并打断事务，保证不留半成品项目。
        if await request.is_disconnected():
            logger.info("取消新建：客户端已断开", extra={"project_id": str(project.id)})
            _discard_source_object(project.id)
            raise ClientDisconnectedException()

        # 上传即触发初稿生成：start_script_ai 内部提交事务后再投递后台任务，
        # 保证后台会话能读到刚建的项目；投递失败不影响上传成功。
        await agent_service.start_script_ai(db, project.id, settings)
        # 页图是编辑态底图：上传后就在后台出图，用户写讲稿时已有画面可看，
        # 之后渲染也能直接复用，不必再跑一次 soffice。
        # 先在本事务里落 queued 再投递：返回的详情自带进度条，前端首屏即可开始轮询，
        # 不用等用户手动刷新才看到缩略图。
        agent_service.mark_page_images_queued(project)
        await db.flush()
        await agent_service.submit_page_images(project.id, project.source_version)
        detail = await agent_service.get_detail(db, project.id, settings, user_id=current_user.id)
    return DataResponse[ProjectDetail](data=detail)


@router.get("/ppt-videos/versions/{version_id}/manifest", summary="版本复用记录（每页 sha256 与命中情况）")
async def get_version_manifest(
    version_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ManifestResponse]:
    with _translate_errors():
        version = await agent_service.get_version(db, version_id)
    return DataResponse[ManifestResponse](data=agent_service.version_manifest(version))


@router.get("/ppt-videos/versions/{version_id}/file", summary="下载/播放成片 MP4（支持 Range）")
async def download_version(
    version_id: uuid.UUID,
    request: Request,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
    inline: bool = Query(False, description="true 时 Content-Disposition 用 inline，供页面内 <video> 直接播放"),
) -> StreamingResponse:
    with _translate_errors():
        version = await agent_service.get_version(db, version_id)
    return _stream_object(version.object_key, "video/mp4", request, file_name=version.file_name, inline=inline)


@router.get("/ppt-videos/{project_id}/source/file", summary="下载当前源 PPT（含页内编辑结果）")
async def download_source_pptx(
    project_id: uuid.UUID,
    request: Request,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    with _translate_errors():
        object_key, file_name = await agent_service.source_download_target(db, project_id)
    return _stream_object(object_key, source_replace.PPTX_CONTENT_TYPE, request, file_name=file_name)


@router.get("/ppt-videos/{project_id}", summary="项目详情（含逐页讲稿、版本、最近任务）")
async def get_project_detail(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectDetail]:
    settings = await agent_config.load_settings()
    with _translate_errors():
        detail = await agent_service.get_detail(db, project_id, settings, user_id=current_user.id)
    return DataResponse[ProjectDetail](data=detail)


@router.patch("/ppt-videos/{project_id}", summary="更新项目默认语言/音色/语速")
async def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectDetail]:
    settings = await agent_config.load_settings()
    with _translate_errors():
        await agent_service.update_project(
            db,
            project_id,
            name=payload.name,
            default_language=payload.default_language,
            default_voice_id=payload.default_voice_id,
            speed=payload.speed,
            updated_by=current_user.id,
        )
        detail = await agent_service.get_detail(db, project_id, settings, user_id=current_user.id)
    return DataResponse[ProjectDetail](data=detail)


@router.delete("/ppt-videos/{project_id}", summary="删除项目（软删除，已生成文件保留）")
async def delete_project(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[MessageResult]:
    with _translate_errors():
        await agent_service.delete_project(db, project_id, current_user.id)
    return DataResponse[MessageResult](data=MessageResult(message="项目已删除"))


# ── 逐页讲稿与试听 ──────────────────────────────────────────────────────────


@router.put("/ppt-videos/{project_id}/slides/{slide_uid}", summary="保存单页讲稿/语言/音色/语速")
async def update_slide(
    project_id: uuid.UUID,
    slide_uid: str,
    payload: SlideUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[SlideItem]:
    with _translate_errors():
        slide = await agent_service.update_slide(
            db,
            project_id,
            slide_uid,
            script_text=payload.script_text,
            language=payload.language,
            voice_id=payload.voice_id,
            speed=payload.speed,
            highlight_style=payload.highlight_style,
            highlight_color=payload.highlight_color,
            highlight_regions=(
                payload.highlight_regions.model_dump() if payload.highlight_regions is not None else None
            ),
            clear_language=payload.clear_language,
            clear_voice=payload.clear_voice,
            clear_speed=payload.clear_speed,
            clear_highlight_style=payload.clear_highlight_style,
            clear_highlight_color=payload.clear_highlight_color,
            clear_highlight_regions=payload.clear_highlight_regions,
            updated_by=current_user.id,
        )
        item = agent_service.slide_item(slide, project_id)
    return DataResponse[SlideItem](data=item)


@router.get(
    "/ppt-videos/{project_id}/slides/{slide_uid}/regions",
    summary="单页可高亮区域清单（区域设置面板用）",
)
async def slide_regions(
    project_id: uuid.UUID,
    slide_uid: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[SlideRegionsResponse]:
    with _translate_errors():
        data = await agent_service.slide_regions(db, project_id, slide_uid)
    return DataResponse[SlideRegionsResponse](data=data)


@router.post("/ppt-videos/{project_id}/slides/{slide_uid}/preview", summary="单页试听（合成或命中缓存）")
async def preview_slide(
    project_id: uuid.UUID,
    slide_uid: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[PreviewResponse]:
    settings = await agent_config.load_settings()
    with _translate_errors():
        slide_no, audio_url, duration_ms, audio_sha256 = await agent_service.preview_slide(
            db, project_id, slide_uid, settings
        )
    return DataResponse[PreviewResponse](
        data=PreviewResponse(
            slide_no=slide_no,
            audio_url=audio_url,
            duration_ms=duration_ms,
            audio_sha256=audio_sha256,
        )
    )


@router.get("/ppt-videos/{project_id}/slides/{slide_no}/image", summary="页面图片（播放器/编辑器大图）")
async def get_slide_image(
    project_id: uuid.UUID,
    slide_no: int,
    request: Request,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    with _translate_errors():
        slide = await agent_service.get_slide(db, project_id, slide_no)
    if not slide.image_object_key:
        raise NotFoundException("页面图片")
    preview_key = agent_service.slide_preview_key(project_id, slide.slide_uid)
    object_key = _first_existing_key(preview_key, slide.image_object_key)
    if object_key is None:
        raise NotFoundException("页面图片")
    return _stream_object(
        object_key,
        "image/jpeg" if object_key == preview_key else "image/png",
        request,
        cache_control=_slide_asset_cache_control(request),
    )


@router.get("/ppt-videos/{project_id}/slides/{slide_no}/thumb", summary="页面缩略图（时间轴/列表）")
async def get_slide_thumb(
    project_id: uuid.UUID,
    slide_no: int,
    request: Request,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    with _translate_errors():
        slide = await agent_service.get_slide(db, project_id, slide_no)
    if not slide.image_object_key:
        raise NotFoundException("页面缩略图")
    thumb_key = agent_service.slide_thumb_key(project_id, slide.slide_uid)
    preview_key = agent_service.slide_preview_key(project_id, slide.slide_uid)
    object_key = _first_existing_key(thumb_key, preview_key, slide.image_object_key)
    if object_key is None:
        raise NotFoundException("页面缩略图")
    content_type = "image/png" if object_key == slide.image_object_key else "image/jpeg"
    return _stream_object(object_key, content_type, request, cache_control=_slide_asset_cache_control(request))


@router.post(
    "/ppt-videos/{project_id}/page-images",
    status_code=202,
    summary="重新生成页图（老项目回填 / 页图异常时手动重试）",
)
async def refresh_page_images(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[PageImagesAccepted]:
    """立刻返回 job_id，进度由前端轮 `GET .../page-images/status`。

    投递前先落 `queued`（同一事务提交）：前端拿到的详情/状态里就带「排队中」，
    刷新页面也不会退回上一次的 done/failed。后台任务认领时会覆盖成 running。
    """
    with _translate_errors():
        project = await agent_service.get_project(db, project_id)
        agent_service.mark_page_images_queued(project)
        await db.flush()
    job_id = await agent_service.submit_page_images(project_id, project.source_version, force=True)
    if job_id is None:
        raise AppException(status_code=503, message="页图任务登记失败，请稍后重试")
    return DataResponse[PageImagesAccepted](data=PageImagesAccepted(job_id=job_id, status="queued"))


@router.get(
    "/ppt-videos/{project_id}/page-images/status",
    summary="页图生成状态（左栏进度条轮询，单表查询）",
)
async def get_page_images_status(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[PageImagesState]:
    with _translate_errors():
        project = await agent_service.get_project(db, project_id)
    return DataResponse[PageImagesState](data=agent_service.page_images_state(project))


@router.get("/ppt-videos/{project_id}/slides/{slide_no}/audio", summary="页面旁白 wav（支持 Range）")
async def get_slide_audio(
    project_id: uuid.UUID,
    slide_no: int,
    request: Request,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    with _translate_errors():
        slide = await agent_service.get_slide(db, project_id, slide_no)
    if not slide.audio_object_key:
        raise NotFoundException("页面旁白")
    return _stream_object(slide.audio_object_key, "audio/wav", request)


# ── 渲染与轮询 ──────────────────────────────────────────────────────────────


@router.post(
    "/ppt-videos/{project_id}/render",
    status_code=202,
    summary="提交渲染任务（立刻返回 job_id，前端轮询 /job）",
)
async def request_render(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RenderAccepted]:
    settings = await agent_config.load_settings()
    with _translate_errors():
        job = await agent_service.request_render(
            db, project_id, settings, requested_by_name=getattr(current_user, "name", None)
        )
    return DataResponse[RenderAccepted](
        data=RenderAccepted(job_id=job.id, status="queued" if job.status == "queued" else "running")
    )


@router.post(
    "/ppt-videos/{project_id}/script-ai",
    status_code=202,
    summary="（重新）生成 AI 讲稿初稿（只填空页，已有讲稿不动）",
)
async def regenerate_script_ai(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    force: bool = Query(default=True, description="强制重发：服务重启后状态可能卡在 running"),
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectDetail]:
    settings = await agent_config.load_settings()
    with _translate_errors():
        await agent_service.start_script_ai(db, project_id, settings, force=force)
        detail = await agent_service.get_detail(db, project_id, settings, user_id=current_user.id)
    return DataResponse[ProjectDetail](data=detail)


@router.get("/ppt-videos/{project_id}/job", summary="最近一次渲染任务状态（轮询）")
async def get_latest_job(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[JobState | None]:
    with _translate_errors():
        await agent_service.get_project(db, project_id)
    job = await agent_queue.get_latest(db, project_id)
    return DataResponse[JobState | None](data=agent_service.job_state(job))


@router.get("/ppt-videos/{project_id}/versions", summary="版本列表")
async def list_versions(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[list[VersionItem]]:
    with _translate_errors():
        await agent_service.get_project(db, project_id)
    versions = await agent_service.list_versions(db, project_id)
    return DataResponse[list[VersionItem]](data=[agent_service.version_item(v) for v in versions])


# ── AI 配置（模型选择 / 个人 Key / 风格指南） ─────────────────────────────────
#
# 路由刻意放在 /ai-configs 而不是 /ppt-videos/ai-config：
# /ppt-videos/{project_id} 是 UUID 路径参数，会把 ai-config 先吃掉返回 422。

PERM_GLOBAL_SETTING = "platform:module-setting:manage"


async def _can_manage_global(db: AsyncSession, user: User) -> bool:
    from app.platform.permission.public_api import has_permission

    return await has_permission(db, user, PERM_GLOBAL_SETTING)


async def _require_global_manage(db: AsyncSession, user: User) -> None:
    if not await _can_manage_global(db, user):
        raise ForbiddenException("只有平台管理员可以修改全局 AI 配置")


def _ai_config_item(row: LLMConfigModel, owner_id: uuid.UUID | None) -> AiConfigItem:
    visibility = (row.visibility or "system").strip() or "system"
    return AiConfigItem(
        id=row.id,
        config_name=row.config_name,
        model_name=row.model_name,
        api_base_url=row.api_base_url,
        visibility=visibility,
        is_active=bool(row.is_active),
        masked_api_key=ai_config.masked_key(row) if visibility == "personal" else "系统预置",
        temperature=float(row.temperature or 0.7),
        timeout_seconds=int(row.timeout_seconds or 60),
        owned=bool(owner_id and row.owner_user_id == owner_id),
    )


async def _ai_config_payload(db: AsyncSession, user: User) -> AiConfigListResponse:
    settings = await agent_config.load_settings()
    rows = await ai_config.visible_configs(db, user.id)
    global_id, global_guide = await ai_config.read_global_settings(db)
    parsed_global_id: uuid.UUID | None = None
    if global_id:
        try:
            parsed_global_id = uuid.UUID(global_id)
        except (TypeError, ValueError):
            parsed_global_id = None
    return AiConfigListResponse(
        items=[_ai_config_item(row, user.id) for row in rows],
        global_default_id=parsed_global_id,
        can_manage_global=await _can_manage_global(db, user),
        global_guide=global_guide,
        script_guide_max_chars=settings.script_guide_max_chars,
    )


@router.get("/ai-configs", summary="AI 配置：系统预置模型 + 我的 Key + 全局讲稿规范")
async def list_ai_configs(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AiConfigListResponse]:
    return DataResponse[AiConfigListResponse](data=await _ai_config_payload(db, current_user))


@router.post("/ai-configs", summary="新增个人 API Key（仅本人可见可用）")
async def create_ai_config(
    payload: AiConfigCreateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AiConfigListResponse]:
    row = await ai_config.create_personal(db, current_user.id, payload)
    await db.commit()
    logger.info("新增个人模型配置: user=%s config=%s", current_user.id, row.id)
    return DataResponse[AiConfigListResponse](data=await _ai_config_payload(db, current_user))


@router.put("/ai-configs/global", summary="设置全局默认模型与全局讲稿规范（需平台管理员）")
async def update_global_ai_settings(
    payload: GlobalAiSettingsRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AiConfigListResponse]:
    await _require_global_manage(db, current_user)
    settings = await agent_config.load_settings()
    global_id, global_guide = await ai_config.read_global_settings(db)

    if payload.clear_global_config:
        global_id = ""
    elif payload.global_config_id is not None:
        config = await get_config_by_id(str(payload.global_config_id), "text", str(current_user.id))
        if not config:
            raise NotFoundException("模型配置")
        global_id = str(config.id)

    if payload.clear_global_guide:
        global_guide = ""
    elif payload.global_guide is not None:
        guide = payload.global_guide.strip()
        if len(guide) > settings.script_guide_max_chars:
            raise BadRequestException(f"讲稿规范最多 {settings.script_guide_max_chars} 字")
        global_guide = guide

    await ai_config.save_setting(db, ai_config.SETTING_GLOBAL_CONFIG_ID, global_id, "全局默认讲稿模型配置 id")
    await ai_config.save_setting(db, ai_config.SETTING_GLOBAL_GUIDE, global_guide, "全局讲稿风格指南")
    await db.commit()
    return DataResponse[AiConfigListResponse](data=await _ai_config_payload(db, current_user))


@router.post("/ai-configs/test", summary="连通性测试（测表单值或已保存的个人配置）")
async def test_ai_config(
    payload: AiConfigTestRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AiConfigTestResponse]:
    if payload.config_id is not None:
        config = await get_config_by_id(str(payload.config_id), "text", str(current_user.id))
        if not config:
            raise NotFoundException("模型配置")
        ok, message = await ai_config.test_connection(
            config.api_base_url,
            config.model_name,
            config.api_key or "",
        )
    else:
        if not (payload.api_base_url and payload.model_name and payload.api_key):
            raise BadRequestException("请填写接口地址、模型名与 API Key")
        ok, message = await ai_config.test_connection(payload.api_base_url, payload.model_name, payload.api_key)
    return DataResponse[AiConfigTestResponse](data=AiConfigTestResponse(ok=ok, message=message))


@router.patch("/ai-configs/{config_id}", summary="修改个人 API Key")
async def update_ai_config(
    config_id: uuid.UUID,
    payload: AiConfigUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AiConfigListResponse]:
    row = await ai_config.get_personal(db, str(config_id), current_user.id)
    if not row:
        raise NotFoundException("个人模型配置")
    await ai_config.update_personal(db, row, payload, current_user.id)
    await db.commit()
    return DataResponse[AiConfigListResponse](data=await _ai_config_payload(db, current_user))


@router.delete("/ai-configs/{config_id}", summary="删除个人 API Key")
async def delete_ai_config(
    config_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[AiConfigListResponse]:
    row = await ai_config.get_personal(db, str(config_id), current_user.id)
    if not row:
        raise NotFoundException("个人模型配置")
    await ai_config.delete_personal(db, row, current_user.id)
    await db.commit()
    return DataResponse[AiConfigListResponse](data=await _ai_config_payload(db, current_user))


@router.put("/ppt-videos/{project_id}/ai", summary="项目级模型覆盖与讲稿规范（留空即继承全局）")
async def update_project_ai_settings(
    project_id: uuid.UUID,
    payload: ProjectAiSettingsRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ProjectDetail]:
    settings = await agent_config.load_settings()
    with _translate_errors():
        await agent_service.update_project_ai(
            db,
            project_id,
            llm_config_id=str(payload.llm_config_id) if payload.llm_config_id else None,
            script_guide=payload.script_guide,
            clear_config=payload.clear_config,
            clear_guide=payload.clear_guide,
            updated_by=current_user.id,
        )
        await db.commit()
        detail = await agent_service.get_detail(db, project_id, settings, user_id=current_user.id)
    return DataResponse[ProjectDetail](data=detail)


# ── 讲稿改写与修订 ──────────────────────────────────────────────────────────


@router.post("/ppt-videos/{project_id}/script-rewrite", summary="按模式改写讲稿（补空页/按指令/单页/全部）")
async def rewrite_scripts(
    project_id: uuid.UUID,
    payload: ScriptRewriteRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[ScriptRewriteResult]:
    settings = await agent_config.load_settings()
    with _translate_errors():
        result = await agent_service.rewrite_scripts(
            db,
            project_id,
            mode=payload.mode,
            slide_uids=[str(item) for item in payload.slide_uids],
            instruction=payload.instruction,
            background=payload.background,
            settings=settings,
            user_id=current_user.id,
            requested_by_name=getattr(current_user, "name", None),
        )
    return DataResponse[ScriptRewriteResult](data=result)


@router.get("/ppt-videos/{project_id}/revisions", summary="讲稿修订记录（可回滚）")
async def list_script_revisions(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_READ)),
    limit: int = Query(30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[RevisionListResponse]:
    with _translate_errors():
        items = await agent_service.list_script_revisions(db, project_id, limit)
    return DataResponse[RevisionListResponse](data=RevisionListResponse(items=items))


@router.post("/ppt-videos/{project_id}/revisions/{revision_id}/rollback", summary="回滚到某次改写之前")
async def rollback_script_revision(
    project_id: uuid.UUID,
    revision_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[MessageResult]:
    with _translate_errors():
        restored = await agent_service.rollback_script_revision(db, project_id, revision_id)
        await db.commit()
    return DataResponse[MessageResult](data=MessageResult(message=f"已回滚 {restored} 页讲稿"))


# ── 换源（重传整份 PPT） ────────────────────────────────────────────────────


@router.post("/ppt-videos/{project_id}/source", summary="上传新 PPT 并比对页序列（不改动现有数据）")
async def preview_source_replace(
    project_id: uuid.UUID,
    file: Annotated[UploadFile, File(description="新的 PPT 文件（.ppt / .pptx）")],
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[SourceDiffSummary]:
    file_bytes = await _read_upload(file, agent_config.MAX_UPLOAD_BYTES)
    _check_ppt_magic(file.filename or "", file_bytes)
    filename = file.filename or "presentation.pptx"
    with _translate_errors():
        diff = await agent_service.preview_source_replace(db, project_id, file_bytes, filename)
    return DataResponse[SourceDiffSummary](data=diff)


@router.post("/ppt-videos/{project_id}/source/apply", summary="应用换源：未变页保留讲稿与音频，变更页自动重写")
async def apply_source_replace(
    project_id: uuid.UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    auto_rewrite: bool = Query(True, description="是否自动重写变更页与新增页讲稿"),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[SourceApplyResult]:
    settings = await agent_config.load_settings()
    with _translate_errors():
        result = await agent_service.apply_source_replace(
            db,
            project_id,
            settings,
            requested_by_name=getattr(current_user, "name", None),
            user_id=current_user.id,
            auto_rewrite=auto_rewrite,
        )
    return DataResponse[SourceApplyResult](data=result)


# ── 轻量页级编辑 ────────────────────────────────────────────────────────────


@router.get("/ppt-videos/{project_id}/slides/{slide_uid}/shapes", summary="可编辑文本框/图片清单")
async def list_editable_shapes(
    project_id: uuid.UUID,
    slide_uid: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[EditableShapeList]:
    with _translate_errors():
        shapes = await agent_service.list_slide_shapes(db, project_id, slide_uid)
    return DataResponse[EditableShapeList](data=shapes)


@router.put("/ppt-videos/{project_id}/slides/{slide_uid}/edit-text", summary="改文本框文字（不保证版式）")
async def edit_slide_text(
    project_id: uuid.UUID,
    slide_uid: str,
    payload: SlideEditTextRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[SlideEditResult]:
    with _translate_errors():
        result = await agent_service.edit_slide(
            db,
            project_id,
            slide_uid,
            {"type": "text", "shape": payload.shape_index, "text": payload.text},
            requested_by_name=getattr(current_user, "name", None),
            user_id=current_user.id,
        )
        await db.commit()
    return DataResponse[SlideEditResult](data=result)


@router.post("/ppt-videos/{project_id}/slides/{slide_uid}/edit-image", summary="替换某张图片（保留位置尺寸）")
async def edit_slide_image(
    project_id: uuid.UUID,
    slide_uid: str,
    current_user: RequiredUser,
    shape_index: Annotated[int, Form(ge=0)],
    file: Annotated[UploadFile, File(description="替换图片（png/jpg/webp）")],
    ctx: PermissionContext = Depends(require_permission(PERM_MANAGE)),
    db: AsyncSession = Depends(get_db),
) -> DataResponse[SlideEditResult]:
    if (file.filename or "").rsplit(".", 1)[-1].lower() not in {"png", "jpg", "jpeg", "webp"}:
        raise BadRequestException("仅支持 png / jpg / webp 图片")
    image_bytes = await _read_upload(file, MAX_IMAGE_BYTES)
    with _translate_errors():
        result = await agent_service.edit_slide(
            db,
            project_id,
            slide_uid,
            {
                "type": "image",
                "shape": shape_index,
                "image_bytes": image_bytes,
            },
            requested_by_name=getattr(current_user, "name", None),
            user_id=current_user.id,
        )
        await db.commit()
    return DataResponse[SlideEditResult](data=result)


# ── 上传校验 ────────────────────────────────────────────────────────────────

_PPTX_MAGIC = b"PK\x03\x04"
_PPT_MAGIC = b"\xd0\xcf\x11\xe0"
MAX_IMAGE_BYTES = 10 * 1024 * 1024


async def _read_upload(file: UploadFile, limit: int) -> bytes:
    """分块读取并累计限流，避免整块读进来才发现超限。"""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = await file.read(STREAM_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise BadRequestException(f"文件超过 {limit // (1024 * 1024)}MB 上限")
        chunks.append(chunk)
    return b"".join(chunks)


def _check_ppt_magic(filename: str, data: bytes) -> None:
    """扩展名之外再看文件魔数：改后缀的图片/文本不应进入解析流程。"""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if suffix == "pptx":
        if not data.startswith(_PPTX_MAGIC):
            raise BadRequestException("文件内容不是有效的 .pptx，请重新导出后再上传")
    elif suffix == "ppt":
        if not data.startswith(_PPT_MAGIC):
            raise BadRequestException("文件内容不是有效的 .ppt，请重新导出后再上传")
    else:
        raise BadRequestException("文件格式不支持：仅支持 .ppt 或 .pptx")
