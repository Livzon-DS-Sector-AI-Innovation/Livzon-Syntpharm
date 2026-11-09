"""渲染 worker 进程入口（独立容器，不与 API 抢 CPU）。

启动方式：
    python -m app.modules.agent.worker            # 常驻轮询
    python -m app.modules.agent.worker --once     # 处理一个任务后退出（调试/CI）

处理流程见 `process_job`：源 PPT → PDF → 每页 PNG → 逐页 TTS → 每页 mp4 → concat 成片。
所有中间产物按内容指纹缓存到 MinIO，命中即复用（TC-006 的取证依据）。
"""

import argparse
import asyncio
import logging
import os
import shutil
import signal
import socket
import tempfile
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import async_session_factory, engine
from app.modules.agent import highlight, page_images, queue, render, service
from app.modules.agent.alignment import Layout
from app.modules.agent.cache import (
    Manifest,
    ManifestSlide,
    sha256_file,
    version_file_name,
)
from app.modules.agent.cache import (
    body_key as build_body_key,
)
from app.modules.agent.cache import (
    segment_key as build_segment_key,
)
from app.modules.agent.config import (
    DEFAULTS,
    ENCODER_KEY,
    HIGHLIGHT_STYLE_DIM,
    HIGHLIGHT_STYLE_OUTLINE,
    HIGHLIGHT_STYLE_TEXT_RECOLOR,
    HIGHLIGHT_STYLES,
    PptVideoSettings,
    load_settings,
    normalize_hex_color,
    parse_hex_color,
)
from app.modules.agent.models import (
    JOB_STATUS_SUCCEEDED,
    PAGE_IMAGES_STATUS_DONE,
    PROJECT_STATUS_FAILED,
    PROJECT_STATUS_READY,
    PptVideoJob,
    PptVideoProject,
    PptVideoSegment,
    PptVideoSlide,
    PptVideoVersion,
)

logger = logging.getLogger(__name__)

WORKER_ID = f"{socket.gethostname()}-{os.getpid()}"
POLL_INTERVAL_SECONDS = 3
STALE_SECONDS = 600
#: 阶段进度分段（与前端 `STAGE_LABEL` 一一对应）：解析 5 → 出图 10 → 逐页合成 10~85
#: → 拼接 88 → 上传 92 → 完成由 `queue.mark_succeeded` 置 done/100。
PROGRESS_START = 5
PROGRESS_RENDER = 10
PROGRESS_TTS_END = 85
PROGRESS_CONCAT = 88
PROGRESS_UPLOAD = 92


class JobFailedError(RuntimeError):
    """任务级失败（消息会回写到 job.error_message 并展示给用户）。"""


async def _load_project(session: AsyncSession, project_id: uuid.UUID) -> PptVideoProject:
    project = await session.get(PptVideoProject, project_id)
    if project is None:
        raise JobFailedError("项目已删除，任务终止")
    return project


async def _load_slides(session: AsyncSession, project_id: uuid.UUID) -> list[PptVideoSlide]:
    slides = await session.scalars(
        select(PptVideoSlide)
        .where(PptVideoSlide.project_id == project_id, PptVideoSlide.is_deleted.is_(False))
        .order_by(PptVideoSlide.slide_no)
    )
    return list(slides)


def _download(module: str, object_key: str, target: Path) -> Path:
    payload = storage.get_object(module, object_key)
    if payload is None:
        raise JobFailedError(f"对象存储中缺少文件：{object_key}")
    data, _ = payload
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return target


async def _resolve_slide_images(
    project: PptVideoProject,
    slides: list[PptVideoSlide],
    source_path: Path,
    work_dir: Path,
    settings: PptVideoSettings,
) -> list[Path]:
    """取页图：已与当前源一致时直接下载，否则转一次 PDF 再拆图。

    页图在上传后就会异步生成，正常情况这里一次转换都不做；
    缓存缺页（老项目、对象丢失、指纹不符）时回退到重新转换，不能让渲染失败。
    返回列表按「源 PPT 页序」排列，与 `pdf_to_pngs` 的输出一致。
    """
    if page_images.page_images_fresh(project, slides):
        try:
            return await asyncio.to_thread(page_images.download_slide_images, project.id, slides, work_dir / "png")
        except Exception:  # noqa: BLE001 - 缓存不可用就重转，渲染不能因此失败
            logger.warning("页图缓存不可用，回退到重新转换: project=%s", project.id, exc_info=True)
    pdf_path = await asyncio.to_thread(page_images.ensure_source_pdf, project.source_sha256, source_path, work_dir)
    # 与页图任务走同一个函数（逐页 pdftoppm），只是这里不需要进度回调：
    # 两条路径的字体与转换参数必须完全一致，否则预览和成片会不一样。
    return await asyncio.to_thread(render.render_pdf_pages, pdf_path, work_dir / "png", settings.render_dpi)


async def process_job(session: AsyncSession, job: PptVideoJob, settings: PptVideoSettings) -> None:
    """执行一个渲染任务；异常一律向上抛，由调用方落库。"""
    render.ensure_tools()
    project = await _load_project(session, job.project_id)
    slides = await _load_slides(session, job.project_id)
    if not slides:
        raise JobFailedError("项目没有页面，无法渲染")

    engine_name, engine_version = service.current_engine(settings)
    work_dir = Path(tempfile.mkdtemp(prefix=f"pptvideo-job-{job.id.hex[:8]}-"))
    try:
        await queue.heartbeat(session, job.id, "parse", PROGRESS_START)
        await session.commit()

        source_path = _download(service.BUCKET_MODULE, project.source_object_key, work_dir / "source.pptx")
        await queue.heartbeat(session, job.id, "render", PROGRESS_RENDER)
        await session.commit()

        images = await _resolve_slide_images(project, slides, source_path, work_dir, settings)
        if len(images) != len(slides):
            raise JobFailedError(f"PPT 渲染出 {len(images)} 页，与讲稿页数 {len(slides)} 不一致")

        total = len(slides)
        segment_paths: list[str | Path] = []
        manifest_slides: list[ManifestSlide] = []
        head_rendered_key = ""
        body_keys: list[str] = []

        async def _prepare_page(slide: Any, image_path: Path) -> _PreparedPage:
            """本页的语音 + 分镜 + 指纹：纯计算与网络 IO，不碰 session，可以并发。"""
            started = time.perf_counter()
            image_sha = sha256_file(image_path)
            effective = service.resolve_effective(slide, project, engine_name, engine_version)
            if not effective.script:
                raise JobFailedError(f"第 {slide.slide_no} 页讲稿为空")
            page_audio = await service.prepare_page_audio(
                slide, project, settings, engine_name, engine_version, work_dir
            )
            plan = _build_highlight_plan(
                effective.script,
                slide.layout,
                page_audio,
                settings,
                highlight.highlight_active(
                    settings.highlight_enabled,
                    bool(getattr(project, "highlight_override_enabled", False)),
                    bool(getattr(slide, "highlight_override_enabled", False)),
                ),
                getattr(slide, "highlight_regions", None),
            )
            _log_fallback_usage(project.id, slide.slide_no, plan)
            # 有高亮时画面是多段静帧序列，页图 sha256 无法代表画面，必须叠加视觉指纹
            # （分句映射 + 布局 + 样式）：只算分句会漏掉「改样式/挪版式但句子没变」的情况，
            # 旧片段被复用后高亮会静默失效。
            paint = _resolve_highlight_paint(settings, slide, project)
            # 指纹必须带完整样式参数（样式/颜色/压暗/描边/染色强度），
            # 只带样式名会让「改了颜色但句子没变」的旧片段被复用。
            visual_key = highlight.visual_fingerprint(plan, slide.layout, paint.fingerprint) if plan.has_boxes else ""
            return _PreparedPage(
                slide=slide,
                image_path=image_path,
                image_sha=image_sha,
                page_audio=page_audio,
                plan=plan,
                paint=paint,
                segment_fp=build_segment_key(image_sha, page_audio.audio_key, ENCODER_KEY, visual_key),
                prepare_ms=int((time.perf_counter() - started) * 1000),
            )

        # 页级流水线：一次备好一批（默认 2 页）的语音与分镜，再串行出帧落库。
        # 语音是网络等待、出帧是 CPU 密集，两者错开跑既压时长又不抢核；
        # 串行段保证 AsyncSession 始终单协程使用。
        concurrency = max(1, min(settings.page_concurrency, 3))
        prepared: list[_PreparedPage] = []
        prepared_from = 0

        for index, slide in enumerate(slides):
            if index >= prepared_from + len(prepared):
                end = min(total, index + concurrency)
                batch = slides[index:end]
                batch_images: list[Path] = []
                for batch_slide in batch:
                    # 页图按「当前源 PPT 页序」取，而不是按展示顺序取：
                    # 换源后 slide_no 会被重排，source_index 才是这张图真正的位置。
                    image_index = batch_slide.source_index or batch_slide.slide_no
                    if image_index < 1 or image_index > len(images):
                        raise JobFailedError(f"第 {batch_slide.slide_no} 页在源 PPT 中找不到对应的第 {image_index} 页")
                    batch_images.append(images[image_index - 1])
                prepared = list(
                    await asyncio.gather(
                        *(
                            _prepare_page(batch_slide, batch_image)
                            for batch_slide, batch_image in zip(batch, batch_images, strict=True)
                        )
                    )
                )
                prepared_from = index

            item = prepared[index - prepared_from]
            page_started = time.perf_counter()
            image_path = item.image_path
            image_sha = item.image_sha
            page_audio = item.page_audio
            audio_fp = page_audio.audio_key
            audio_path = page_audio.path
            audio_sha = page_audio.sha256
            duration_ms = page_audio.duration_ms
            plan = item.plan
            paint = item.paint
            segment_fp = item.segment_fp
            cached = await session.scalar(
                select(PptVideoSegment).where(
                    PptVideoSegment.segment_key == segment_fp, PptVideoSegment.is_deleted.is_(False)
                )
            )
            segment_path = work_dir / "segments" / f"{segment_fp}.mp4"
            segment_hit = (
                cached is not None
                and storage.stat_object(service.BUCKET_MODULE, service.segment_object_key(segment_fp)) is not None
            )

            if segment_hit:
                _download(service.BUCKET_MODULE, service.segment_object_key(segment_fp), segment_path)
                segment_duration = cached.duration_ms if cached else duration_ms
            else:
                if plan.has_boxes:
                    segment_duration = await asyncio.to_thread(
                        _render_highlighted_segment,
                        image_path,
                        audio_path,
                        segment_path,
                        plan,
                        slide.layout,
                        settings,
                        paint,
                        work_dir,
                        segment_fp,
                    )
                else:
                    segment_duration = await asyncio.to_thread(
                        render.build_slide_segment,
                        image_path,
                        audio_path,
                        segment_path,
                        duration_ms,
                        settings.head_padding_ms,
                        settings.tail_padding_ms,
                        settings.ffmpeg_threads,
                    )
                storage.upload_file(
                    service.BUCKET_MODULE, service.segment_object_key(segment_fp), str(segment_path), "video/mp4"
                )
                await _upsert_segment(session, segment_fp, image_sha, audio_sha, segment_duration, segment_path)

            # 页图按「稳定页身份」落库：换源后 slide_no 会重排，用页码做 key 会互相覆盖
            if not await asyncio.to_thread(page_images.slide_assets_ready, project.id, slide, image_sha):
                await asyncio.to_thread(page_images.publish_slide_images, project.id, slide, image_path, work_dir)
            slide.image_object_key = service.slide_image_key(project.id, slide.slide_uid)
            slide.image_sha256 = image_sha
            slide.audio_key = audio_fp
            slide.audio_object_key = service.audio_object_key(audio_fp)
            slide.audio_sha256 = audio_sha
            slide.duration_ms = duration_ms

            segment_paths.append(segment_path)
            manifest_slides.append(
                ManifestSlide(
                    slide_no=slide.slide_no,
                    slide_uid=str(slide.slide_uid),
                    image_sha256=image_sha,
                    audio_sha256=audio_sha,
                    segment_sha256=segment_fp,
                    duration_ms=segment_duration,
                    cache_hit=segment_hit,
                )
            )
            if index == 0:
                head_rendered_key = segment_fp
            else:
                body_keys.append(segment_fp)

            logger.info(
                "页渲染完成: project=%s slide=%s prepare_ms=%s render_ms=%s cache_hit=%s",
                project.id,
                slide.slide_no,
                item.prepare_ms,
                int((time.perf_counter() - page_started) * 1000),
                segment_hit,
            )

            progress = PROGRESS_RENDER + int((index + 1) / total * (PROGRESS_TTS_END - PROGRESS_RENDER))
            await queue.heartbeat(session, job.id, "tts", progress)
            await session.commit()

        # 页图已随本次渲染对齐到当前源：下次重渲可直接跳过整本转换。
        # 渲染管线指纹也要一起写，否则 `page_images_fresh` 会一直判过期、
        # 每次渲染都白跑一遍 soffice。
        project.page_images_version = project.source_version
        project.page_images_renderer = render.RENDERER_KEY
        # 本次渲染自己就产出了一整套页图，顺带把页图进度收尾成 done：
        # 否则并发的页图任务被杀/重启后，左栏进度条会一直转到 30 分钟超时才变失败，
        # 而画面其实早就能看了。
        project.page_images_status = PAGE_IMAGES_STATUS_DONE
        project.page_images_progress = 100
        project.page_images_total = total
        project.page_images_done = total
        project.page_images_error = None

        await queue.heartbeat(session, job.id, "concat", PROGRESS_CONCAT)
        await session.commit()
        final_path = work_dir / "output.mp4"
        await asyncio.to_thread(render.concat_segments, segment_paths, final_path, work_dir / "concat.txt")
        await queue.heartbeat(session, job.id, "upload", PROGRESS_UPLOAD)
        await session.commit()

        version = await _save_version(
            session,
            project,
            final_path,
            manifest_slides,
            head_rendered_key,
            build_body_key(body_keys),
            engine_name,
            engine_version,
        )
        await queue.mark_succeeded(session, job.id, version.id)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)


def _log_fallback_usage(project_id: Any, slide_no: int, plan: highlight.HighlightPlan) -> None:
    """记录每页兜底命中数：验收「讲到的地方一定有高亮」时看这个比例是否在下降。"""
    sources = [step.fallback for step in plan.steps if step.fallback in ("guess", "page")]
    if not sources:
        return
    logger.info(
        "高亮兜底命中: project=%s slide=%s guess=%s page=%s steps=%s",
        project_id,
        slide_no,
        sources.count("guess"),
        sources.count("page"),
        len(plan.steps),
    )


def _build_highlight_plan(
    script: str,
    layout: Layout | None,
    page_audio: service.PageAudio,
    settings: PptVideoSettings,
    active: bool,
    regions: Any = None,
) -> highlight.HighlightPlan:
    """按旁白音频与页面布局生成页内引导计划；未开启或失败时返回空计划。

    `active` 是三级开关合成结果（见 `highlight.highlight_active`）：模块总闸、
    项目级、本页级任一层没放行就返回空计划，成片保持原图。
    逐段合成时段时间轴直接用各段音频实测时长；退回整页合成时才按字数估算。
    `regions` 是落库的区域配置（区域三态 + 句级微调），坏配置只会退化成自动判定。
    """
    total_ms = page_audio.duration_ms
    if not active or not layout:
        return highlight.HighlightPlan(steps=[], total_ms=total_ms)
    config = highlight.RegionConfig()
    try:
        config = highlight.parse_region_config(regions, layout)
        if page_audio.segmented:
            return highlight.build_plan_for_segments(
                highlight.apply_sentence_rules(page_audio.segments, config),
                layout,
                page_audio.segment_slots_ms,
                total_ms,
                min_dwell_ms=settings.highlight_min_dwell_ms,
                coverage_threshold=settings.highlight_text_match_coverage,
                config=config,
            )
        return highlight.build_plan(script, layout, total_ms, settings.highlight_max_steps, config)
    except Exception:  # noqa: BLE001 - 引导失败不能让整条视频渲不出来
        logger.exception("页内视觉引导计划生成失败，退化为整页常亮")
        return highlight.HighlightPlan(steps=[], total_ms=total_ms)


@dataclass
class _PreparedPage:
    """一页的「输入侧」产物：语音、分镜、指纹。全部不依赖 session，可并发准备。"""

    slide: Any
    image_path: Path
    image_sha: str
    page_audio: service.PageAudio
    plan: highlight.HighlightPlan
    paint: "_HighlightPaint"
    segment_fp: str
    prepare_ms: int = 0


@dataclass(frozen=True)
class _HighlightPaint:
    """一次出帧真正用到的样式参数（已合并「页级 → 项目级 → 模块设置」）。"""

    style: str
    color: str
    dim_alpha: int
    accent: tuple[int, int, int]
    outline_px: int
    fill_alpha: int
    recolor_strength: int

    @property
    def fingerprint(self) -> str:
        """帧缓存指纹：颜色/强度变一点，画面就不同，旧片段必须失效。"""
        return f"{self.style}:{self.color}:{self.dim_alpha}:{self.outline_px}:{self.fill_alpha}:{self.recolor_strength}"


def _resolve_highlight_paint(settings: PptVideoSettings, slide: Any, project: Any) -> _HighlightPaint:
    """合并页级 > 项目级 > 模块设置；本级未启用则整级跳过，非法覆盖值逐级回落。

    「本级是否启用」看 `highlight_override_enabled`，不能看样式/颜色是否为空：
    用户关掉开关时刻意保留了已选的值，只按空值判断会把关闭的层级又算回来。

    某一级写了非法值时也必须继续往下一级找，而不是把坏值当成空——否则坏颜色
    会被当成「没配」而回落，坏样式却会顶掉上一级的合法值。
    """
    levels: list[Any] = []
    if bool(getattr(slide, "highlight_override_enabled", False)):
        levels.append(slide)
    if bool(getattr(project, "highlight_override_enabled", False)):
        levels.append(project)
    style = ""
    for level in levels:
        style = str(getattr(level, "highlight_style", None) or "").strip()
        if style in HIGHLIGHT_STYLES:
            break
    if style not in HIGHLIGHT_STYLES:
        style = settings.highlight_style
    color = ""
    for candidate in [*(getattr(level, "highlight_color", None) for level in levels), settings.highlight_color]:
        color = normalize_hex_color(str(candidate or ""), "")
        if color:
            break
    if not color:
        color = DEFAULTS.highlight_color
    accent = parse_hex_color(color)
    dim_alpha = settings.highlight_dim_alpha
    outline_px = settings.highlight_outline_px
    fill_alpha = settings.highlight_fill_alpha
    recolor_strength = settings.highlight_recolor_strength
    if style == HIGHLIGHT_STYLE_TEXT_RECOLOR:
        # 文字染色：背景不压暗、不描边。
        # 页内文字在解析阶段已经定位到框，命中框里的字直接换色即可；
        # 再画一圈矩形描边会露出「机器标注」的痕迹，用户明确要求去掉。
        # 图片/图表不是文字、无法染色，仍保留极淡主色底（0 可关）。
        return _HighlightPaint(style, color, 0, accent, 0, fill_alpha, recolor_strength)
    if style == HIGHLIGHT_STYLE_DIM:
        return _HighlightPaint(style, color, dim_alpha, accent, 0, 0, 0)
    if style == HIGHLIGHT_STYLE_OUTLINE:
        return _HighlightPaint(style, color, 0, accent, outline_px, 0, 0)
    return _HighlightPaint(style, color, dim_alpha, accent, outline_px, 0, 0)


#: 区域 `text` 档在页级未配染色强度时的兜底强度（0-100）
_REGION_TEXT_STRENGTH = 100


def _box_paint(box: highlight.HighlightBox, base: _HighlightPaint) -> render.RegionPaint:
    """把单个区域的画法折算成渲染层参数。

    未配区域效果（`mode` 为空）时严格沿用改造前口径——文本染色 or 淡色底由 kind 决定，
    保证没配过的页逐像素不变。
    """
    mode = box.mode or ""
    if mode == highlight.REGION_MODE_AREA:
        accent = parse_hex_color(box.color) if box.color else base.accent
        alpha = box.fill_alpha if box.fill_alpha is not None else highlight.DEFAULT_REGION_FILL_ALPHA
        return render.RegionPaint(accent, text=False, fill_alpha=alpha, recolor_strength=0)
    if mode == highlight.REGION_MODE_TEXT:
        accent = parse_hex_color(box.color) if box.color else base.accent
        return render.RegionPaint(
            accent, text=True, fill_alpha=0, recolor_strength=base.recolor_strength or _REGION_TEXT_STRENGTH
        )
    if base.recolor_strength > 0 and box.is_text:
        return render.RegionPaint(base.accent, text=True, fill_alpha=0, recolor_strength=base.recolor_strength)
    return render.RegionPaint(base.accent, text=False, fill_alpha=base.fill_alpha, recolor_strength=0)


def _render_highlighted_segment(
    image_path: Path,
    audio_path: Path,
    segment_path: Path,
    plan: highlight.HighlightPlan,
    layout: Layout | None,
    settings: PptVideoSettings,
    paint: _HighlightPaint,
    work_dir: Path,
    segment_fp: str,
) -> int:
    """逐段预合成高亮静帧，再交给同一套编码参数出片。

    `-c copy` 拼接链路对画面来源不敏感，只要时长与编码参数一致即可，
    所以这里不需要改动 concat 逻辑。
    """
    size = highlight.slide_size(layout)
    frame_dir = work_dir / "highlight" / segment_fp
    frame_dir.mkdir(parents=True, exist_ok=True)
    # 一页要出多帧：整页图只解码一次，省掉每帧一次 PNG 解码（页数越多越明显）
    with Image.open(image_path) as handle:
        base_image = handle.convert("RGB")

    frames: list[tuple[Path, int]] = []
    for index, step in enumerate(plan.steps):
        boxes = [(box.left, box.top, box.width, box.height) for box in step.boxes]
        kinds = [box.kind for box in step.boxes]
        # 逐框取画法：区域三态各自生效，未配过的框仍按页级样式走
        paints = [_box_paint(box, paint) for box in step.boxes]
        frame_path = render.compose_highlight_frame(
            image_path,
            frame_dir / f"{index:02d}.png",
            boxes,
            size,
            paint.dim_alpha,
            paint.accent,
            paint.outline_px,
            kinds=kinds,
            paints=paints,
            base_image=base_image,
        )
        frames.append((frame_path, step.duration_ms))

    return render.build_highlighted_segment(
        frames,
        audio_path,
        segment_path,
        plan.total_ms,
        settings.head_padding_ms,
        settings.tail_padding_ms,
        work_dir / "highlight" / f"{segment_fp}.txt",
        settings.ffmpeg_threads,
    )


async def _upsert_segment(
    session: AsyncSession,
    segment_fp: str,
    image_sha: str,
    audio_sha: str,
    duration_ms: int,
    segment_path: Path,
) -> None:
    existing = await session.scalar(
        select(PptVideoSegment).where(PptVideoSegment.segment_key == segment_fp, PptVideoSegment.is_deleted.is_(False))
    )
    if existing is None:
        session.add(
            PptVideoSegment(
                id=uuid.uuid4(),
                segment_key=segment_fp,
                image_sha256=image_sha,
                audio_sha256=audio_sha,
                encoder_key=ENCODER_KEY,
                duration_ms=duration_ms,
                object_key=service.segment_object_key(segment_fp),
                file_size=segment_path.stat().st_size,
            )
        )
    else:
        existing.duration_ms = duration_ms
    await session.flush()


async def _save_version(
    session: AsyncSession,
    project: PptVideoProject,
    final_path: Path,
    manifest_slides: list[ManifestSlide],
    head_key: str,
    body_key_value: str,
    engine_name: str,
    engine_version: str,
) -> PptVideoVersion:
    next_no = (
        await session.scalar(
            select(func.coalesce(func.max(PptVideoVersion.version_no), 0)).where(
                PptVideoVersion.project_id == project.id
            )
        )
        or 0
    ) + 1
    object_key = service.video_object_key(project.id, next_no)
    storage.upload_file(service.BUCKET_MODULE, object_key, str(final_path), "video/mp4")

    file_name = version_file_name(project.name, next_no, head_key)
    duration_ms = sum(slide.duration_ms for slide in manifest_slides)
    manifest = Manifest(
        project_id=str(project.id),
        head_key=head_key,
        body_key_value=body_key_value,
        encoder_key=ENCODER_KEY,
        slides=manifest_slides,
        total_duration_ms=duration_ms,
    )
    version = PptVideoVersion(
        id=uuid.uuid4(),
        project_id=project.id,
        version_no=next_no,
        file_name=file_name,
        object_key=object_key,
        file_size=final_path.stat().st_size,
        duration_ms=duration_ms,
        file_sha256=sha256_file(final_path),
        head_key=head_key,
        body_key=body_key_value,
        manifest=manifest.as_dict(),
    )
    session.add(version)

    slides = await _load_slides(session, project.id)
    body_input = service.compute_body_input_key(slides, project, engine_name, engine_version)
    project.head_key = head_key
    project.body_key = body_key_value
    project.body_input_key = body_input
    project.status = PROJECT_STATUS_READY
    project.last_error = None
    await session.flush()
    return version


async def _handle_failure(session: AsyncSession, job: PptVideoJob, message: str) -> None:
    project = await session.get(PptVideoProject, job.project_id)
    retry = (job.attempts or 0) < (job.max_attempts or 3)
    await queue.mark_failed(session, job.id, message, retry)
    if project is not None:
        project.last_error = message[:2000]
        if not retry:
            project.status = PROJECT_STATUS_FAILED
    await session.commit()


async def process_once(worker_id: str = WORKER_ID) -> bool:
    """抢占并处理一个任务；返回是否真的处理了任务。"""
    settings = await load_settings()
    async with async_session_factory() as session:
        await queue.requeue_stale(session, STALE_SECONDS)
        await session.commit()
        job = await queue.claim(session, worker_id)
        if job is None:
            await session.commit()
            return False
        await session.commit()
        job_id = job.id
        logger.info("claimed job %s (project %s)", job_id, job.project_id)
        try:
            await process_job(session, job, settings)
        except Exception as exc:  # noqa: BLE001 - 任何异常都要落库并继续消费下一个任务
            logger.exception("job %s failed", job_id)
            message = str(exc) or exc.__class__.__name__
            refreshed = await session.get(PptVideoJob, job_id)
            if refreshed is not None and refreshed.status != JOB_STATUS_SUCCEEDED:
                await _handle_failure(session, refreshed, message)
        return True


async def run_forever(stop_event: asyncio.Event) -> None:
    logger.info("ppt-video worker started: %s", WORKER_ID)
    while not stop_event.is_set():
        try:
            handled = await process_once()
        except Exception:  # noqa: BLE001 - 轮询不能因单次异常退出
            logger.exception("worker loop error")
            handled = False
        if not handled:
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=POLL_INTERVAL_SECONDS)
            except TimeoutError:
                continue
    logger.info("ppt-video worker stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="PPT 配音视频渲染 worker")
    parser.add_argument("--once", action="store_true", help="只处理一个任务后退出")
    parser.add_argument("--verbose", action="store_true", help="输出 DEBUG 日志")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )

    if args.once:
        handled = asyncio.run(process_once())
        asyncio.run(engine.dispose())
        print("processed" if handled else "no job")
        return

    stop_event = asyncio.Event()

    def _stop(*_: object) -> None:
        stop_event.set()

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    async def _main() -> None:
        try:
            await run_forever(stop_event)
        finally:
            await engine.dispose()

    asyncio.run(_main())


if __name__ == "__main__":
    main()
