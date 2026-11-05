"""PPT 配音视频业务编排。

API 层只做参数校验与响应组装，所有跨表/跨存储的动作落在这里：
项目创建（解析 PPT + 讲稿切分）、讲稿保存、试听、入队渲染、版本与复用记录查询。
真正的渲染在 `worker.py` 里跑（独立容器），本模块不调用 ffmpeg。
"""

import asyncio
import json
import logging
import re
import shutil
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.modules.agent import (
    ai_config,
    editor,
    highlight,
    page_images,
    parser,
    queue,
    render,
    rewrite,
    script_ai,
    source_replace,
    tts,
)
from app.modules.agent.cache import (
    Manifest,
    body_input_key,
    normalize_script,
    script_key,
    segment_audio_key,
    sha256_bytes,
    sha256_file,
    slide_input_key,
    voice_key,
)
from app.modules.agent.cache import (
    audio_key as build_audio_key,
)
from app.modules.agent.config import (
    DEFAULTS,
    HIGHLIGHT_STYLES,
    MAX_SCRIPT_CHARS,
    MODULE_CODE,
    SCRIPT_GUIDE_MAX_CHARS,
    PptVideoSettings,
    load_settings,
    normalize_hex_color,
)
from app.modules.agent.models import (
    PAGE_IMAGES_STATUS_DONE,
    PAGE_IMAGES_STATUS_FAILED,
    PAGE_IMAGES_STATUS_QUEUED,
    PAGE_IMAGES_STATUS_RUNNING,
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
    PptVideoSegment,
    PptVideoSlide,
    PptVideoVersion,
)
from app.modules.agent.schemas import (
    EditableShapeItem,
    EditableShapeList,
    HighlightRegionsPayload,
    JobState,
    ManifestResponse,
    ManifestSlideItem,
    PageImagesState,
    ProjectDetail,
    ProjectSummary,
    ReuseSummary,
    RevisionItem,
    ScriptAiState,
    ScriptRewriteResult,
    ScriptRuntime,
    SlideEditResult,
    SlideItem,
    SlideRegionItem,
    SlideRegionsResponse,
    SlideSentenceHint,
    SourceApplyResult,
    SourceDiffSummary,
    VersionItem,
)
from app.modules.agent.voices import is_voice_in_language, list_voices

logger = logging.getLogger(__name__)

BUCKET_MODULE = MODULE_CODE

# 下载文件名里不允许出现的字符：路径分隔符会变成目录，换行会截断响应头
_FILENAME_ILLEGAL = re.compile(r'[/\\\r\n"]+')

GUIDE_MAX_CHARS = SCRIPT_GUIDE_MAX_CHARS

#: 页图任务超过这么久没有任何进度写入，就认为进程已死（见 `_page_images_stale`）
PAGE_IMAGES_STALE_SECONDS = 30 * 60
#: 排队中超过这么久还没被任务认领，说明投递丢了（防线：不让进度条永远转）
PAGE_IMAGES_QUEUE_STALE_SECONDS = 2 * 60

#: 区域面板回给前端的句子数上限（与 `MAX_SENTENCE_RULES` 同量级，够配到每一句）
_SENTENCE_PREVIEW_STEPS = 32


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


def slide_preview_key(project_id: uuid.UUID, slide_uid: uuid.UUID) -> str:
    """页图预览版（JPEG）：给编辑器中间画面用。

    成片仍读 PNG 原件，所以换预览格式不会让已缓存的视频片段失效。
    """
    return f"ppt-video/{project_id}/slides/{slide_uid}.jpg"


def slide_thumb_key(project_id: uuid.UUID, slide_uid: uuid.UUID) -> str:
    """时间轴/列表缩略图（JPEG，320 宽），避免为 96px 的格子拉整张原图。"""
    return f"ppt-video/{project_id}/slides/{slide_uid}-thumb.jpg"


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


def thumb_url(project_id: uuid.UUID, slide_no: int, version_token: str | None = None) -> str:
    """缩略图地址：同样带内容指纹，时间轴换页后不会被旧图顶住。"""
    base = f"/api/v1/agent/ppt-videos/{project_id}/slides/{slide_no}/thumb"
    return f"{base}?v={version_token[:12]}" if version_token else base


def audio_url(project_id: uuid.UUID, slide_no: int, version_token: str | None = None) -> str:
    base = f"/api/v1/agent/ppt-videos/{project_id}/slides/{slide_no}/audio"
    return f"{base}?v={version_token[:12]}" if version_token else base


def download_url(version_id: uuid.UUID) -> str:
    return f"/api/v1/agent/ppt-videos/versions/{version_id}/file"


def preview_url(version_id: uuid.UUID) -> str:
    """页面内预览地址：同一个媒体端点，只把 Disposition 切成 inline。

    播放器要用 src 直接播，attachment 会让浏览器走下载；两者共用 Range 实现，
    所以不加新端点，避免两处流式逻辑各自演化。
    """
    return f"{download_url(version_id)}?inline=1"


def source_download_url(project_id: uuid.UUID) -> str:
    """当前源 PPT 下载地址；前端只用这个字段，不自己拼路径。"""
    return f"/api/v1/agent/ppt-videos/{project_id}/source/file"


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


# ── 旁白音频（逐段合成） ────────────────────────────────────────────────────


def segment_audio_object_key(fingerprint: str) -> str:
    """段级音频按内容寻址：改一句只重合成那一句，其余句子直接命中。"""
    return f"ppt-video/audio-seg/{fingerprint}.wav"


def page_audio_meta_key(audio_fingerprint: str) -> str:
    """段时长元数据：命中页音频时靠它还原高亮时间轴，不必再读一遍每段音频。"""
    return f"ppt-video/audio/{audio_fingerprint}.json"


@dataclass(frozen=True)
class PageAudio:
    """一页旁白的音频产物 + 出帧需要的段信息。"""

    path: Path
    duration_ms: int
    sha256: str
    audio_key: str
    #: 分段结果；为空表示退回「整页单段合成」，出帧走旧的字数估算
    segments: list[highlight.ScriptSegment] = field(default_factory=list)
    segment_durations_ms: list[int] = field(default_factory=list)
    pause_ms: int = 0

    @property
    def segmented(self) -> bool:
        return len(self.segments) > 1 and len(self.segments) == len(self.segment_durations_ms)

    @property
    def segment_slots_ms(self) -> list[int]:
        """出帧用：每段占用时长 = 该段音频 + 段后停顿（末段不含停顿）。"""
        slots = [max(0, int(value)) for value in self.segment_durations_ms]
        if len(slots) > 1 and self.pause_ms > 0:
            slots = [value + self.pause_ms for value in slots[:-1]] + [slots[-1]]
        return slots


def page_audio_plan(
    slide: PptVideoSlide,
    effective: EffectiveVoice,
    settings: PptVideoSettings,
) -> tuple[list[highlight.ScriptSegment], int, str]:
    """决定本页走逐段合成还是整页合成，并给出页音频指纹。

    只有「高亮开启 + 逐段合成开启 + 段数 > 1」才分段；否则指纹与改造前完全一致，
    老项目的音频缓存继续命中。
    """
    segments: list[highlight.ScriptSegment] = []
    if settings.highlight_enabled and settings.segment_tts_enabled:
        segments = highlight.resolve_segments(
            effective.script,
            slide.layout or {},
            slide.script_segments,
            settings.highlight_max_steps,
        )
    if len(segments) <= 1:
        return [], 0, build_audio_key(effective.script_sha256, effective.voice_fingerprint)

    pause_ms = settings.segment_pause_ms
    texts = "\n".join(segment.text for segment in segments)
    boundaries = sha256_bytes(f"segments\n{pause_ms}\n{texts}".encode())[:16]
    return (
        segments,
        pause_ms,
        # 段边界与段间停顿都会改变波形，必须进指纹，否则改了分段还会复用旧音频
        build_audio_key(effective.script_sha256, effective.voice_fingerprint, f"seg{boundaries}"),
    )


def _download_object(object_key: str, target: Path) -> bool:
    """按对象 key 落盘；不存在返回 False。"""
    payload = storage.get_object(BUCKET_MODULE, object_key)
    if payload is None:
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload[0])
    return True


def _load_segment_durations(audio_fingerprint: str) -> list[int]:
    payload = storage.get_object(BUCKET_MODULE, page_audio_meta_key(audio_fingerprint))
    if payload is None:
        return []
    try:
        data = json.loads(payload[0].decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        logger.warning("页音频元数据损坏，按未命中处理: %s", audio_fingerprint)
        return []
    raw = data.get("durations") if isinstance(data, dict) else None
    if not isinstance(raw, list):
        return []
    durations: list[int] = []
    for value in raw:
        try:
            durations.append(max(0, int(value)))
        except (TypeError, ValueError):
            return []
    return durations


async def _ensure_whole_page_audio(
    effective: EffectiveVoice,
    audio_fingerprint: str,
    audio_path: Path,
    engine_name: str,
    sha_hint: str,
) -> PageAudio:
    """整页单段合成（改造前的路径，也是分段失败时的兜底）。"""
    if _download_object(audio_object_key(audio_fingerprint), audio_path):
        sha = sha_hint or await asyncio.to_thread(sha256_file, audio_path)
        duration = await asyncio.to_thread(tts.wav_duration_ms, audio_path)
        return PageAudio(audio_path, duration, sha, audio_fingerprint)

    try:
        result = await asyncio.to_thread(
            tts.synthesize_to_wav,
            effective.script,
            effective.language,
            effective.voice_id,
            effective.speed,
            audio_path,
            engine_name,
        )
    except tts.TtsError as exc:
        raise ServiceError(str(exc)) from exc

    data = await asyncio.to_thread(audio_path.read_bytes)
    await asyncio.to_thread(
        storage.upload_object,
        BUCKET_MODULE,
        audio_object_key(audio_fingerprint),
        data,
        len(data),
        "audio/wav",
    )
    return PageAudio(audio_path, result.duration_ms, result.sha256, audio_fingerprint)


async def _synthesize_by_segments(
    segments: list[highlight.ScriptSegment],
    effective: EffectiveVoice,
    settings: PptVideoSettings,
    engine_name: str,
    audio_fingerprint: str,
    pause_ms: int,
    audio_path: Path,
    work_dir: Path,
) -> PageAudio:
    """逐段合成（段级缓存）→ 拼接页面音频 → 落库 + 写段时长元数据。

    同一页的多段语音并发合成（上限 `tts_concurrency`）：TTS 是网络等待，
    并发不占本机 CPU；任一段失败就整体抛错，由调用方回退到整页单段合成。
    """
    semaphore = asyncio.Semaphore(max(1, settings.tts_concurrency))
    part_paths: list[Path] = [
        work_dir / "audio-seg" / f"{audio_fingerprint}-{index:02d}.wav" for index, _ in enumerate(segments)
    ]

    async def _synthesize_one(index: int, segment: highlight.ScriptSegment) -> int:
        part_path = part_paths[index]
        key = segment_audio_key(segment.text, effective.language, effective.voice_fingerprint)
        async with semaphore:
            if _download_object(segment_audio_object_key(key), part_path):
                return await asyncio.to_thread(tts.wav_duration_ms, part_path)
            result = await asyncio.to_thread(
                tts.synthesize_to_wav,
                segment.text,
                effective.language,
                effective.voice_id,
                effective.speed,
                part_path,
                engine_name,
            )
            part_bytes = await asyncio.to_thread(part_path.read_bytes)
            await asyncio.to_thread(
                storage.upload_object,
                BUCKET_MODULE,
                segment_audio_object_key(key),
                part_bytes,
                len(part_bytes),
                "audio/wav",
            )
            return result.duration_ms

    gathered = await asyncio.gather(
        *(_synthesize_one(index, segment) for index, segment in enumerate(segments)),
        return_exceptions=True,
    )
    durations: list[int] = []
    for item in gathered:
        if isinstance(item, BaseException):
            raise item
        durations.append(int(item))

    merged_path, _joined_ms = await asyncio.to_thread(tts.concat_wavs, part_paths, audio_path, pause_ms)
    duration = await asyncio.to_thread(tts.wav_duration_ms, merged_path)
    wav_bytes = await asyncio.to_thread(merged_path.read_bytes)
    await asyncio.to_thread(
        storage.upload_object,
        BUCKET_MODULE,
        audio_object_key(audio_fingerprint),
        wav_bytes,
        len(wav_bytes),
        "audio/wav",
    )
    meta = json.dumps(
        {"durations": durations, "segments": len(segments), "pause_ms": pause_ms}, ensure_ascii=False
    ).encode()
    await asyncio.to_thread(
        storage.upload_object,
        BUCKET_MODULE,
        page_audio_meta_key(audio_fingerprint),
        meta,
        len(meta),
        "application/json",
    )
    return PageAudio(
        merged_path,
        duration,
        sha256_bytes(wav_bytes),
        audio_fingerprint,
        segments,
        durations,
        pause_ms,
    )


async def prepare_page_audio(
    slide: PptVideoSlide,
    project: PptVideoProject,
    settings: PptVideoSettings,
    engine_name: str,
    engine_version: str,
    work_dir: Path,
) -> PageAudio:
    """合成（或命中缓存）一页旁白；渲染与试听共用，避免两条路径的指纹不一致。

    分段合成出任何问题都退回整页单段合成：单页旁白不该把整条视频带崩。
    """
    effective = resolve_effective(slide, project, engine_name, engine_version)
    if not effective.script:
        raise ServiceError("本页讲稿为空，请先填写后再试听")

    segments, pause_ms, audio_fingerprint = page_audio_plan(slide, effective, settings)
    audio_path = work_dir / "audio" / f"{audio_fingerprint}.wav"
    sha_hint = (slide.audio_sha256 or "") if slide.audio_key == audio_fingerprint else ""

    if not segments:
        return await _ensure_whole_page_audio(effective, audio_fingerprint, audio_path, engine_name, sha_hint)

    durations = _load_segment_durations(audio_fingerprint)
    if _download_object(audio_object_key(audio_fingerprint), audio_path) and len(durations) == len(segments):
        sha = sha_hint or await asyncio.to_thread(sha256_file, audio_path)
        duration = await asyncio.to_thread(tts.wav_duration_ms, audio_path)
        return PageAudio(audio_path, duration, sha, audio_fingerprint, segments, durations, pause_ms)

    try:
        return await _synthesize_by_segments(
            segments, effective, settings, engine_name, audio_fingerprint, pause_ms, audio_path, work_dir
        )
    except Exception:  # noqa: BLE001 - 分段合成任何失败都退回整页，保证出片
        logger.exception(
            "逐段合成失败，退回整页合成: project=%s slide=%s segments=%s",
            project.id,
            slide.slide_no,
            len(segments),
        )
        whole_fingerprint = build_audio_key(effective.script_sha256, effective.voice_fingerprint)
        whole_path = work_dir / "audio" / f"{whole_fingerprint}.wav"
        whole_sha = (slide.audio_sha256 or "") if slide.audio_key == whole_fingerprint else ""
        return await _ensure_whole_page_audio(effective, whole_fingerprint, whole_path, engine_name, whole_sha)


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


def mark_page_images_queued(project: PptVideoProject) -> None:
    """把项目行标成「排队中」，调用方负责 flush/commit。

    页图任务在后台会话里写 running，写进去之前前端只能看到上一轮的状态；上传或换源时先在
    本事务里落 queued，前端拿到的详情就带进度条，可以直接开始轮询，不用等用户手动刷新。
    必须在投递**前**写：投递之后后台任务可能已经认领，再写 queued 会把 running 盖回去。
    """
    project.page_images_status = PAGE_IMAGES_STATUS_QUEUED
    project.page_images_progress = 0
    project.page_images_total = project.slide_count
    project.page_images_done = 0
    project.page_images_error = None


async def submit_page_images(
    project_id: uuid.UUID, expect_version: int = 0, *, force: bool = False
) -> uuid.UUID | None:
    """异步生成页图（编辑态底图）。

    投递失败只记日志：没有页图最坏是「编辑态暂时看不到画面」，
    渲染时会自己转一次，不该阻塞上传。
    """
    return await page_images.submit(project_id, expect_version, force)


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
        preview_url=preview_url(version.id),
        created_at=version.created_at,
    )


def _highlight_regions_payload(slide: PptVideoSlide) -> HighlightRegionsPayload | None:
    """区域配置回显：落库值本应已校验，但老数据/手改库可能带坏值，这里再兜一次。"""
    config = highlight.parse_region_config(getattr(slide, "highlight_regions", None), slide.layout)
    dumped = highlight.dump_region_config(config)
    return HighlightRegionsPayload.model_validate(dumped) if dumped else None


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
        highlight_style=slide.highlight_style,
        highlight_color=slide.highlight_color,
        highlight_regions=_highlight_regions_payload(slide),
        page_text=slide.page_text,
        page_notes=slide.page_notes,
        image_url=image_url(project_id, slide.slide_no, slide.image_sha256) if slide.image_object_key else None,
        thumb_url=thumb_url(project_id, slide.slide_no, slide.image_sha256) if slide.image_object_key else None,
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


def page_images_state(project: PptVideoProject) -> PageImagesState:
    """页图生成状态：全部取自项目列，不再额外查表。

    `page_images_version == source_version` 且渲染指纹一致时页图一定是最新的，此时即使
    状态列还是 idle（老项目升级后没跑过任务）也按 done/100 呈现，
    否则前端会为一个本来就有图的页面显示「重新生成」。
    """
    status = project.page_images_status or "idle"
    progress = project.page_images_progress or 0
    total = project.page_images_total or 0
    done = project.page_images_done or 0
    error = project.page_images_error
    up_to_date = (
        project.page_images_version == project.source_version
        and project.page_images_version > 0
        and project.page_images_renderer == render.RENDERER_KEY
    )
    # 排队 / 正在跑 / 失败的状态必须以状态列为准：否则强制重试一个「内容已最新」的项目时，
    # 这里会把 queued 抹成 done，进度条一出现就消失、失败原因也看不到。
    if up_to_date and status not in (
        PAGE_IMAGES_STATUS_QUEUED,
        PAGE_IMAGES_STATUS_RUNNING,
        PAGE_IMAGES_STATUS_FAILED,
    ):
        status = PAGE_IMAGES_STATUS_DONE
        progress = 100
        total = total or project.slide_count
        done = total
    elif status == PAGE_IMAGES_STATUS_RUNNING and _page_images_stale(project, PAGE_IMAGES_STALE_SECONDS):
        # 进程被杀 / 重启后状态会永远停在 running，前端会无限轮询：超时未推进按失败呈现，
        # 用户点「重试」会重新投递（新任务认领后覆盖这一行）
        status = PAGE_IMAGES_STATUS_FAILED
        error = error or "生成超时或服务已重启，请重试"
        progress = min(progress, 99)
    elif status == PAGE_IMAGES_STATUS_QUEUED and _page_images_stale(project, PAGE_IMAGES_QUEUE_STALE_SECONDS):
        # 投递成功但任务始终没被认领（队列丢任务 / 进程不在）：别让进度条永远停在 0
        status = PAGE_IMAGES_STATUS_FAILED
        error = error or "任务未启动，请重试"
        progress = 0
    return PageImagesState(
        status=status,
        error=error,
        progress=max(0, min(100, progress)),
        done=done,
        total=total,
        job_id=project.page_images_job_id,
    )


def _page_images_stale(project: PptVideoProject, threshold_seconds: int) -> bool:
    """页图任务超过 `threshold_seconds` 没有推进过就认为已经死掉。

    `_set_state` 的单条 UPDATE 会带 `updated_at=now()`，所以活跃任务每出一页都会刷新它；
    运行中取 30 分钟（给大文件 soffice 转换留余量），排队中只给 2 分钟（这时还没有进度可等）。
    """
    if project.updated_at is None:
        return False
    return (datetime.now(UTC) - project.updated_at).total_seconds() > threshold_seconds


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
        page_images=page_images_state(project),
        script_runtime=await script_runtime_state(session, project, settings, user_id),
        source_version=project.source_version or 1,
        source_download_url=source_download_url(project.id),
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
                preview_url=preview_url(latest.id) if latest else "",
                latest_error=project.last_error,
                thumbnail_url=thumb_url(project.id, 1),
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


async def invalidate_slide_segments(session: AsyncSession, slide: PptVideoSlide) -> int:
    """作废某页的片段缓存，保证下次出片按这页「当前的」配置重渲。

    页片段 key 只由「页图 + 音频 + 编码参数 + 视觉指纹」算出。只要指纹漏掉任何一项
    影响画面的配置（历史上新增配置项时忘并进指纹就发生过），旧片段就会被原样复用，
    用户看到的就是「配置保存成功了，成片却没变」，而且排起来毫无线索。
    保存页配置属于低频动作，重渲一页的成本远低于这种静默失效，所以直接作废。

    片段是可再生的中间产物，这里物理删除：留下 is_deleted=True 的行仍占着
    uq_agent_ppt_video_segment_key，worker 重渲时插入同一个 key 会撞唯一约束。
    """
    if not slide.image_sha256:
        return 0
    rows = (
        await session.scalars(
            # 连软删的历史行一起清：它们仍占着 segment_key 的唯一约束，
            # 只删有效行的话，worker 重渲插入同一个 key 会直接撞约束报错。
            select(PptVideoSegment).where(PptVideoSegment.image_sha256 == slide.image_sha256)
        )
    ).all()
    for row in rows:
        try:
            storage.delete_object(BUCKET_MODULE, row.object_key)
        except Exception:  # noqa: BLE001 - 对象删不掉也不能挡住保存：索引行删掉后就不会再命中
            logger.warning("作废页片段对象失败：%s", row.object_key, exc_info=True)
        await session.delete(row)
    if rows:
        await session.flush()
        logger.info("作废页片段缓存：image=%s 共 %d 条", slide.image_sha256[:12], len(rows))
    return len(rows)


async def update_slide(
    session: AsyncSession,
    project_id: uuid.UUID,
    slide_uid: str,
    *,
    script_text: str | None,
    language: str | None,
    voice_id: str | None,
    speed: float | None,
    highlight_style: str | None = None,
    highlight_color: str | None = None,
    highlight_regions: dict[str, Any] | None = None,
    clear_language: bool,
    clear_voice: bool,
    clear_speed: bool,
    clear_highlight_style: bool = False,
    clear_highlight_color: bool = False,
    clear_highlight_regions: bool = False,
    updated_by: uuid.UUID | None,
) -> PptVideoSlide:
    project = await get_project(session, project_id)
    slide = await get_slide_by_uid(session, project_id, slide_uid)
    # 画面相关配置的旧值：保存完对比，动过就让这页的历史片段作废
    prev_visual = (slide.highlight_style, slide.highlight_color, slide.highlight_regions)

    if script_text is not None:
        if len(script_text) > MAX_SCRIPT_CHARS:
            raise ServiceError(f"单页讲稿不能超过 {MAX_SCRIPT_CHARS} 字")
        changed = script_text != (slide.script_text or "")
        slide.script_text = script_text
        slide.script_stale = False
        if changed:
            # 手改后段级绑定与文本不再配套，宁可退回字面匹配，也不能按旧绑定亮错
            slide.script_segments = None
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
    if highlight_style is not None:
        if highlight_style not in HIGHLIGHT_STYLES:
            raise ServiceError(f"高亮样式仅支持 {'/'.join(HIGHLIGHT_STYLES)}")
        slide.highlight_style = highlight_style
    if highlight_color is not None:
        # 空串当作「清除覆盖」，非法值直接拒绝：坏颜色进了渲染只会把画面染脏
        normalized = normalize_hex_color(highlight_color, "")
        if not normalized:
            raise ServiceError("高亮颜色需为 #RRGGBB 格式")
        slide.highlight_color = normalized
    if clear_highlight_style:
        slide.highlight_style = None
    if clear_highlight_color:
        slide.highlight_color = None
    if highlight_regions is not None:
        # 整份替换而不是增量合并：前后端各存一半会对不上，渲染时更难排查。
        # 元素 id 必须能在本页 layout 里找到，否则存进去也亮不出来，直接丢掉。
        config = highlight.parse_region_config(highlight_regions, slide.layout)
        slide.highlight_regions = highlight.dump_region_config(config)
    if clear_highlight_regions:
        slide.highlight_regions = None
    slide.updated_by = updated_by
    if (slide.highlight_style, slide.highlight_color, slide.highlight_regions) != prev_visual:
        # 「保存即生效」的落点：画面配置变了就作废该页片段，下次出片一定重渲这页。
        # 不能只依赖缓存 key 变化——key 里的视觉指纹一旦漏项（或渲染器换了实现），
        # 同样的 key 会把旧画面端回来，用户改完配置看着像没保存成功。
        await invalidate_slide_segments(session, slide)
    await session.flush()
    return slide


async def slide_regions(
    session: AsyncSession,
    project_id: uuid.UUID,
    slide_uid: str,
) -> SlideRegionsResponse:
    """区域设置面板的数据源：页面尺寸 + 可点选元素清单（坐标来自 layout 解析）。

    人工点选只落元素 id，坐标在渲染时按 layout 现算，所以换分辨率、重出片都不会偏。
    """
    slide = await get_slide_by_uid(session, project_id, slide_uid)
    size = highlight.slide_size(slide.layout)
    page_width, page_height = size or (0, 0)
    items = [
        SlideRegionItem(
            element_id=ref.element_id,
            kind=ref.box.kind,
            label=highlight.kind_label(ref.box.kind),
            text=(ref.text or "").strip()[: highlight.ELEMENT_TEXT_CHARS],
            left=ref.box.left,
            top=ref.box.top,
            width=ref.box.width,
            height=ref.box.height,
        )
        for ref in highlight.iter_elements(slide.layout)
    ]
    sentences = highlight.split_sentences(slide.script_text or "", max_steps=_SENTENCE_PREVIEW_STEPS)
    config = highlight.parse_region_config(slide.highlight_regions, slide.layout)
    # 句级目标沿用出帧时的同一份解析结果，面板上显示的「这句亮什么」才不会和成片不一致
    stored_targets = {
        "".join(segment.text.split()): list(segment.targets)
        for segment in highlight.resolve_segments(
            slide.script_text or "",
            slide.layout,
            slide.script_segments,
            _SENTENCE_PREVIEW_STEPS,
            config,
        )
    }
    hints: list[SlideSentenceHint] = []
    # 框 → 元素 id：面板上要能列出「这句实际亮了哪几块」，才好一键改回不亮
    id_by_box = {
        (ref.box.left, ref.box.top, ref.box.width, ref.box.height): ref.element_id
        for ref in highlight.element_index(slide.layout).values()
    }
    for sentence in sentences:
        targets = stored_targets.get("".join(sentence.split()), [])
        boxes, fallback = highlight.boxes_for_segment_with_source(
            highlight.ScriptSegment(text=sentence, targets=tuple(targets)),
            slide.layout,
            config=config,
        )
        elements = [
            id_by_box[(box.left, box.top, box.width, box.height)]
            for box in boxes
            if (box.left, box.top, box.width, box.height) in id_by_box
        ]
        hints.append(
            SlideSentenceHint(text=sentence, targets=targets, fallback=fallback, elements=sorted(set(elements)))
        )
    return SlideRegionsResponse(
        page_width=page_width,
        page_height=page_height,
        items=items,
        # 逐句微调用的句子必须与渲染时切法一致，所以由服务端切好回给前端
        sentences=sentences,
        sentence_hints=hints,
        image_sha256=slide.image_sha256,
    )


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

    _segments, _pause_ms, fingerprint = page_audio_plan(slide, effective, settings)
    if slide.audio_key == fingerprint and slide.audio_object_key:
        return (
            slide.slide_no,
            audio_url(project_id, slide.slide_no, slide.audio_sha256),
            slide.duration_ms or 0,
            slide.audio_sha256 or "",
        )

    work_dir = Path(tempfile.mkdtemp(prefix=f"preview-{project_id.hex[:8]}-"))
    try:
        page_audio = await prepare_page_audio(slide, project, settings, engine_name, engine_version, work_dir)
        slide.audio_object_key = audio_object_key(page_audio.audio_key)
        slide.audio_key = page_audio.audio_key
        slide.audio_sha256 = page_audio.sha256
        slide.duration_ms = page_audio.duration_ms
        await session.flush()
        return (
            slide.slide_no,
            audio_url(project_id, slide.slide_no, page_audio.sha256),
            page_audio.duration_ms,
            page_audio.sha256,
        )
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

    # 换源/页内编辑后立刻刷新页图：编辑器里的画面必须跟着新源走。
    # 带上期望版本号，任务会等到主事务提交、新版本可见后再出图，不会按旧源白转一次。
    # 先把「排队中」写进项目行（随本次事务一起提交）：前端拿到新详情就能显示进度条并开始轮询。
    # 这一步不能交给后台会话——那时本事务还没提交，独立会话的 UPDATE 会命中 0 行。
    mark_page_images_queued(project)
    await session.flush()
    if await page_images.submit(project_id, result.source_version) is None:
        # 投递失败（登记 job 抛错）时把排队态改掉：不然要等 2 分钟超时前端才看到失败
        project.page_images_status = PAGE_IMAGES_STATUS_FAILED
        project.page_images_error = "页图任务投递失败，请重试"
        await session.flush()

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
    payload = await asyncio.to_thread(storage.get_object, BUCKET_MODULE, project.source_object_key)
    if payload is None:
        raise ServiceError("源 PPT 已丢失，请重新上传")
    data, _content_type = payload
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


async def source_download_target(session: AsyncSession, project_id: uuid.UUID) -> tuple[str, str]:
    """源 PPT 下载目标：(对象 key, 下载文件名)。

    文件名只用项目名与版本号，不拼用户上传的原名，避免中文/特殊字符带来的路径问题；
    项目名本身是用户输入，路径分隔符与换行会破坏 Content-Disposition，统一替换掉。
    """
    project = await get_project(session, project_id)
    total = await asyncio.to_thread(storage.stat_object, BUCKET_MODULE, project.source_object_key)
    if not total:
        raise NotFoundError("源 PPT 已丢失，请重新上传")
    version = project.source_version or 1
    safe_name = _FILENAME_ILLEGAL.sub("_", project.name or "ppt").strip() or "ppt"
    return project.source_object_key, f"{safe_name}-v{version}.pptx"


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
        await load_settings(),
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
