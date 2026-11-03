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
import uuid
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import async_session_factory, engine
from app.modules.agent import highlight, queue, render, service, tts
from app.modules.agent.alignment import Layout
from app.modules.agent.cache import (
    Manifest,
    ManifestSlide,
    sha256_file,
    version_file_name,
)
from app.modules.agent.cache import (
    audio_key as build_audio_key,
)
from app.modules.agent.cache import (
    body_key as build_body_key,
)
from app.modules.agent.cache import (
    segment_key as build_segment_key,
)
from app.modules.agent.config import ENCODER_KEY, PptVideoSettings, load_settings
from app.modules.agent.models import (
    JOB_STATUS_SUCCEEDED,
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
PROGRESS_START = 5
PROGRESS_END = 90


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
        pdf_path = await asyncio.to_thread(render.pptx_to_pdf, source_path, work_dir / "pdf", work_dir / "lo-profile")
        images = await asyncio.to_thread(render.pdf_to_pngs, pdf_path, work_dir / "png", settings.render_dpi)
        if len(images) != len(slides):
            raise JobFailedError(f"PPT 渲染出 {len(images)} 页，与讲稿页数 {len(slides)} 不一致")

        total = len(slides)
        segment_paths: list[str | Path] = []
        manifest_slides: list[ManifestSlide] = []
        head_rendered_key = ""
        body_keys: list[str] = []

        for index, slide in enumerate(slides):
            # 页图按「当前源 PPT 页序」取，而不是按展示顺序取：
            # 换源后 slide_no 会被重排，source_index 才是这张图真正的位置。
            image_index = slide.source_index or slide.slide_no
            if image_index < 1 or image_index > len(images):
                raise JobFailedError(f"第 {slide.slide_no} 页在源 PPT 中找不到对应的第 {image_index} 页")
            image_path = images[image_index - 1]
            image_sha = sha256_file(image_path)
            effective = service.resolve_effective(slide, project, engine_name, engine_version)
            if not effective.script:
                raise JobFailedError(f"第 {slide.slide_no} 页讲稿为空")

            audio_fp = build_audio_key(effective.script_sha256, effective.voice_fingerprint)
            audio_path = work_dir / "audio" / f"{audio_fp}.wav"
            audio_hit = storage.stat_object(service.BUCKET_MODULE, service.audio_object_key(audio_fp)) is not None
            if audio_hit:
                _download(service.BUCKET_MODULE, service.audio_object_key(audio_fp), audio_path)
                # 库里记过同一音频指纹就直接复用，没有则现算，保证 audio_sha 一定是字符串
                audio_sha = (slide.audio_sha256 if slide.audio_key == audio_fp else None) or sha256_file(audio_path)
            else:
                result = await asyncio.to_thread(
                    tts.synthesize_to_wav,
                    effective.script,
                    effective.language,
                    effective.voice_id,
                    effective.speed,
                    audio_path,
                    engine_name,
                )
                audio_sha = result.sha256
                storage.upload_file(
                    service.BUCKET_MODULE, service.audio_object_key(audio_fp), str(audio_path), "audio/wav"
                )

            duration_ms = await asyncio.to_thread(_wav_duration_ms, audio_path)
            plan = _build_highlight_plan(effective.script, slide.layout, duration_ms, settings)
            # 有高亮时画面是多段静帧序列，页图 sha256 无法代表画面，必须叠加视觉指纹
            # （分句映射 + 布局 + 样式）：只算分句会漏掉「改样式/挪版式但句子没变」的情况，
            # 旧片段被复用后高亮会静默失效。
            visual_key = (
                highlight.visual_fingerprint(plan, slide.layout, settings.highlight_style) if plan.has_boxes else ""
            )
            segment_fp = build_segment_key(image_sha, audio_fp, ENCODER_KEY, visual_key)
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
            page_image_key = service.slide_image_key(project.id, slide.slide_uid)
            storage.upload_file(
                service.BUCKET_MODULE,
                page_image_key,
                str(image_path),
                "image/png",
            )
            slide.image_object_key = page_image_key
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

            progress = PROGRESS_START + int((index + 1) / total * (PROGRESS_END - PROGRESS_START))
            await queue.heartbeat(session, job.id, "tts", progress)
            await session.commit()

        final_path = work_dir / "output.mp4"
        await asyncio.to_thread(render.concat_segments, segment_paths, final_path, work_dir / "concat.txt")
        await queue.heartbeat(session, job.id, "upload", 95)
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


def _build_highlight_plan(
    script: str,
    layout: Layout | None,
    duration_ms: int,
    settings: PptVideoSettings,
) -> highlight.HighlightPlan:
    """按旁白时长与页面布局生成页内引导计划；未开启时返回空计划。"""
    if not settings.highlight_enabled or not layout:
        return highlight.HighlightPlan(steps=[], total_ms=duration_ms)
    try:
        return highlight.build_plan(script, layout, duration_ms, settings.highlight_max_steps)
    except Exception:  # noqa: BLE001 - 引导失败不能让整条视频渲不出来
        logger.exception("页内视觉引导计划生成失败，退化为整页常亮")
        return highlight.HighlightPlan(steps=[], total_ms=duration_ms)


def _highlight_style_options(style: str) -> tuple[int, tuple[int, int, int], int]:
    """样式 → (压暗透明度, 描边色, 描边像素)。"""
    accent = (86, 69, 212)
    if style == "dim":
        return 150, accent, 0
    if style == "outline":
        return 0, accent, 4
    return 150, accent, 4


def _render_highlighted_segment(
    image_path: Path,
    audio_path: Path,
    segment_path: Path,
    plan: highlight.HighlightPlan,
    layout: Layout | None,
    settings: PptVideoSettings,
    work_dir: Path,
    segment_fp: str,
) -> int:
    """逐段预合成高亮静帧，再交给同一套编码参数出片。

    `-c copy` 拼接链路对画面来源不敏感，只要时长与编码参数一致即可，
    所以这里不需要改动 concat 逻辑。
    """
    dim_alpha, accent, outline_px = _highlight_style_options(settings.highlight_style)
    size = highlight.slide_size(layout)
    frame_dir = work_dir / "highlight" / segment_fp
    frame_dir.mkdir(parents=True, exist_ok=True)

    frames: list[tuple[Path, int]] = []
    for index, step in enumerate(plan.steps):
        boxes = [(box.left, box.top, box.width, box.height) for box in step.boxes]
        frame_path = render.compose_highlight_frame(
            image_path,
            frame_dir / f"{index:02d}.png",
            boxes,
            size,
            dim_alpha,
            accent,
            outline_px,
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


def _wav_duration_ms(path: Path) -> int:
    import wave

    with wave.open(str(path), "rb") as handle:
        return int(handle.getnframes() / handle.getframerate() * 1000)


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
