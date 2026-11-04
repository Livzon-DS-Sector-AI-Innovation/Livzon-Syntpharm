"""换源：重传整份 PPT、对齐页序列、按差异落库。

对外两个入口：

- `prepare()`：上传到 pending 区 + 解析 + 出差异预览，**不落库**
- `apply()`  ：按预览结果在一次事务内重排页序、标记变更、自动重写

为什么不做「单页替换图片」：PPT 是唯一真源，单页替换后下次整份更新必然冲突。
整份重传的实际成本只有一次 LibreOffice 转 PDF，TTS 与 ffmpeg 只跑变更页。

三条硬约束：

1. 页身份用 `slide_uid`，`slide_no` 只是展示序号，一次事务内整体重排；
2. 未变页保留讲稿 / 音频 / 页图 fingerprint，缓存才能命中；
3. 变更页与新增页标记 `script_stale` 并清空音频指纹，由改写任务补稿。
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.modules.agent import parser
from app.modules.agent.alignment import AlignedDiff, PageSnapshot, align
from app.modules.agent.cache import sha256_bytes
from app.modules.agent.config import MODULE_CODE
from app.modules.agent.models import (
    REVISION_STATUS_RUNNING,
    REWRITE_MODE_SOURCE_REPLACE,
    PptVideoProject,
    PptVideoScriptRevision,
    PptVideoSlide,
)

logger = logging.getLogger(__name__)

BUCKET_MODULE = MODULE_CODE
PPTX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.presentationml.presentation"


class SourceReplaceError(ValueError):
    """换源失败，message 直接回给前端。"""


@dataclass
class PreparedSource:
    """预览结果：新文件的解析产物 + 差异。"""

    parsed: list[parser.ParsedSlide]
    diff: AlignedDiff
    pending_key: str
    sha256: str
    filename: str | None


@dataclass
class ApplyResult:
    revision_id: uuid.UUID | None
    diff: AlignedDiff
    rewrite_uids: list[str]
    source_version: int
    slide_count: int


def pending_object_key(project_id: uuid.UUID, filename: str | None = None) -> str:
    """待应用的 PPT 对象 key。后缀要跟着原文件走，.ppt 不能按 .pptx 解析。"""
    suffix = Path(filename or "").suffix.lower()
    if suffix not in (".ppt", ".pptx"):
        suffix = ".pptx"
    return f"ppt-video/{project_id}/pending/source{suffix}"


def _read_pending(project_id: uuid.UUID) -> tuple[bytes, str]:
    """取回待应用文件；两种后缀都探一遍，避免上传 .ppt 后找不到。"""
    for suffix in (".pptx", ".ppt"):
        payload = storage.get_object(BUCKET_MODULE, pending_object_key(project_id, f"x{suffix}"))
        if payload is None:
            continue
        data, _content_type = payload
        return data, f"source{suffix}"
    raise SourceReplaceError("未找到待应用的 PPT，请重新上传")


def versioned_source_key(project_id: uuid.UUID, version: int) -> str:
    return f"ppt-video/{project_id}/source-v{version}.pptx"


def _snapshots(slides: list[PptVideoSlide]) -> list[PageSnapshot]:
    return [
        PageSnapshot(
            index=slide.source_index or slide.slide_no,
            page_text=slide.page_text or "",
            notes=slide.page_notes or "",
            layout=slide.layout or [],
            fingerprint=slide.page_fingerprint,
        )
        for slide in sorted(slides, key=lambda item: item.slide_no)
    ]


async def _load_slides(session: AsyncSession, project_id: uuid.UUID) -> list[PptVideoSlide]:
    rows = await session.scalars(
        select(PptVideoSlide)
        .where(PptVideoSlide.project_id == project_id, PptVideoSlide.is_deleted.is_(False))
        .order_by(PptVideoSlide.slide_no)
    )
    return list(rows.all())


def _parse_bytes(file_bytes: bytes, filename: str) -> tuple[list[parser.ParsedSlide], bytes]:
    """解析上传文件，并返回归一化后的 .pptx 字节。

    上传的可能是 .ppt，直接原样存成 source-vN.pptx 会让后续编辑/渲染拿到坏文件，
    所以统一以 LibreOffice 转出的 pptx 作为新源版本。
    """
    work_dir = Path(tempfile.mkdtemp(prefix="pptvideo-replace-"))
    try:
        suffix = Path(filename).suffix.lower() or ".pptx"
        raw_path = work_dir / f"source{suffix}"
        raw_path.write_bytes(file_bytes)
        pptx_path = parser.convert_to_pptx(raw_path, work_dir)
        return parser.parse_pptx(pptx_path), pptx_path.read_bytes()
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


async def prepare(
    session: AsyncSession,
    project: PptVideoProject,
    file_bytes: bytes,
    filename: str,
) -> PreparedSource:
    """上传到 pending 区并产出差异预览。"""
    if not file_bytes:
        raise SourceReplaceError("上传的文件为空")
    if Path(filename).suffix.lower() not in (".ppt", ".pptx"):
        raise SourceReplaceError("文件格式不支持：仅支持 .ppt 或 .pptx")

    parsed, _ = _parse_bytes(file_bytes, filename)
    if not parsed:
        raise SourceReplaceError("PPT 中没有可识别的幻灯片")

    old_slides = await _load_slides(session, project.id)
    diff = align(
        _snapshots(old_slides),
        [
            PageSnapshot(
                index=item.slide_no,
                page_text=item.text,
                notes=item.notes,
                layout=item.layout,
                fingerprint=item.fingerprint,
            )
            for item in parsed
        ],
    )

    pending_key = pending_object_key(project.id, filename)
    storage.upload_object(
        BUCKET_MODULE,
        pending_key,
        file_bytes,
        len(file_bytes),
        PPTX_CONTENT_TYPE if filename.lower().endswith(".pptx") else "application/vnd.ms-powerpoint",
    )
    logger.info(
        "换源预览: project=%s old=%s new=%s 变更=%s 新增=%s 删除=%s",
        project.id,
        diff.old_count,
        diff.new_count,
        len(diff.changed),
        len(diff.added),
        len(diff.removed),
    )
    return PreparedSource(
        parsed=parsed,
        diff=diff,
        pending_key=pending_key,
        sha256=sha256_bytes(file_bytes),
        filename=filename,
    )


async def apply(
    session: AsyncSession,
    project: PptVideoProject,
    *,
    requested_by_name: str | None = None,
) -> ApplyResult:
    """读取 pending 文件，按对齐结果落库。整个动作在一个事务内完成。"""
    file_bytes, pending_name = _read_pending(project.id)
    parsed, pptx_bytes = _parse_bytes(file_bytes, pending_name)
    old_slides = await _load_slides(session, project.id)
    diff = align(
        _snapshots(old_slides),
        [
            PageSnapshot(
                index=item.slide_no,
                page_text=item.text,
                notes=item.notes,
                layout=item.layout,
                fingerprint=item.fingerprint,
            )
            for item in parsed
        ],
    )

    by_index = {slide.source_index or slide.slide_no: slide for slide in old_slides}
    new_version = (project.source_version or 1) + 1
    new_source_key = versioned_source_key(project.id, new_version)

    storage.upload_object(BUCKET_MODULE, new_source_key, pptx_bytes, len(pptx_bytes), PPTX_CONTENT_TYPE)

    rewrite_uids: list[str] = []
    affected_uids: list[str] = []
    before: dict[str, str] = {}

    # 1) 未变页：只更新页序，讲稿/音频/页图指纹全部保留
    for old_index, new_index in diff.unchanged:
        slide = by_index.get(old_index)
        if slide is None:
            continue
        slide.slide_no = new_index
        slide.source_index = new_index

    # 2) 变更页：换页内容、标记过期、清空音频（页图 key 变了也不需要保留旧图）
    for old_index, new_index in diff.changed:
        slide = by_index.get(old_index)
        if slide is None:
            continue
        item = parsed[new_index - 1]
        before[str(slide.slide_uid)] = slide.script_text or ""
        affected_uids.append(str(slide.slide_uid))
        rewrite_uids.append(str(slide.slide_uid))
        slide.slide_no = new_index
        slide.source_index = new_index
        slide.page_text = (item.text or "")[:5000] or None
        slide.page_notes = (item.notes or "")[:5000] or None
        slide.layout = item.layout
        slide.page_fingerprint = item.fingerprint
        # 版式变了，旧的元素 id 指向的东西可能已经不同，绑定必须作废（讲稿保留、改由字面兜底）
        slide.script_segments = None
        slide.script_stale = True
        slide.image_object_key = None
        slide.image_sha256 = None
        slide.audio_object_key = None
        slide.audio_key = None
        slide.audio_sha256 = None
        slide.duration_ms = 0

    # 3) 删除页：软删，讲稿保留在修订快照里
    for old_index in diff.removed:
        slide = by_index.get(old_index)
        if slide is None:
            continue
        before[str(slide.slide_uid)] = slide.script_text or ""
        affected_uids.append(str(slide.slide_uid))
        slide.is_deleted = True
        slide.script_stale = True

    # 4) 新增页：新建记录并进改写队列
    for new_index in diff.added:
        item = parsed[new_index - 1]
        slide = PptVideoSlide(
            id=uuid.uuid4(),
            project_id=project.id,
            slide_uid=uuid.uuid4(),
            slide_no=new_index,
            source_index=new_index,
            page_text=(item.text or "")[:5000] or None,
            page_notes=(item.notes or "")[:5000] or None,
            layout=item.layout,
            page_fingerprint=item.fingerprint,
            script_stale=True,
            script_text="",
            script_source="",
        )
        session.add(slide)
        before[str(slide.slide_uid)] = ""
        affected_uids.append(str(slide.slide_uid))
        rewrite_uids.append(str(slide.slide_uid))

    project.source_version = new_version
    project.source_object_key = new_source_key
    project.source_sha256 = sha256_bytes(pptx_bytes)
    project.slide_count = len(parsed)
    project.updated_at = func.now()
    project.body_input_key = None  # 正文变了，旧的可复用判断必须失效
    project.head_key = None

    revision = PptVideoScriptRevision(
        project_id=project.id,
        mode=REWRITE_MODE_SOURCE_REPLACE,
        instruction=None,
        model_name=None,
        provider=None,
        scope=affected_uids,
        before=before,
        after={},
        status=REVISION_STATUS_RUNNING,
        progress=0,
        source_version=project.source_version,
        applied=True,
        requested_by_name=requested_by_name,
    )
    session.add(revision)
    await session.flush()
    await session.commit()

    logger.info(
        "换源应用完成: project=%s v%s 页数=%s 待重写=%s",
        project.id,
        new_version,
        len(parsed),
        len(rewrite_uids),
    )
    return ApplyResult(
        revision_id=revision.id,
        diff=diff,
        rewrite_uids=rewrite_uids,
        source_version=new_version,
        slide_count=len(parsed),
    )


def diff_payload(diff: AlignedDiff) -> dict[str, Any]:
    return diff.to_dict()
