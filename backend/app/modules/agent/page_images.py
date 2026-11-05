"""上传后异步生成页图（编辑态底图）。

为什么单独一个后台任务：

- 页图只是「让用户在网页里看得见画面」，不该阻塞上传，也不该等到点渲染才出现；
- 渲染 worker 是单并发队列，把出图塞进去会堵住真正的成片渲染；
  所以走 `core.jobs` 的一次性后台任务（与 `script_ai` 同一套入口）。

中间 PDF 按源文件指纹内容寻址缓存：页图任务与渲染任务共用同一份，
第二次转换（改一页重渲、同一份 PPT 再传一次）可以直接跳过 soffice。

幂等约束：页图对象 key 由 `slide_uid` 决定，重复执行只会覆盖成同样的内容；
写回数据库前重新校验项目 `source_version`，避免把旧源的图写到新源上。
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import tempfile
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import storage
from app.core.database import async_session_factory
from app.core.jobs import submit_job_safe
from app.modules.agent import render
from app.modules.agent.cache import sha256_bytes, sha256_file
from app.modules.agent.config import MODULE_CODE, load_settings
from app.modules.agent.models import (
    PAGE_IMAGES_STATUS_DONE,
    PAGE_IMAGES_STATUS_FAILED,
    PAGE_IMAGES_STATUS_IDLE,
    PAGE_IMAGES_STATUS_RUNNING,
    PptVideoProject,
    PptVideoSlide,
)

logger = logging.getLogger(__name__)

#: `core.background_jobs` 里的任务名
JOB_NAME = f"{MODULE_CODE}.ppt-video.page-images"

#: 后台任务启动时等主事务提交的最长时间（秒）
PROJECT_WAIT_SECONDS = 10

#: 轮询项目是否可见的间隔（秒）
PROJECT_WAIT_INTERVAL_SECONDS = 0.5

#: 投递后延迟执行（秒）：连续保存时把多次编辑合并成一次出图
PAGE_IMAGES_DEBOUNCE_SECONDS = 2.0

#: 进度分段（与前端文案一一对应）：转换 0→40，逐页拆图 40→85，编码上传 85→99，提交 100
PROGRESS_CONVERT_END = 40
PROGRESS_SPLIT_START = 40
PROGRESS_SPLIT_END = 85
PROGRESS_UPLOAD_START = 85
PROGRESS_UPLOAD_END = 99

#: 出图会调用 soffice，很吃 CPU。后台任务可能被批量上传同时触发，
#: 串行执行，避免把 API 进程的响应拖慢（渲染有独立队列，不受影响）。
_CONVERSION_SLOT = asyncio.Semaphore(1)


def _ensure_page_image_tools() -> None:
    """页图只依赖 soffice + poppler，不检查 ffmpeg——backend 镜像里没有它。

    字体也要一起校验：页图是在 backend 进程里出的，镜像少装 Liberation/Carlito 或
    别名 conf 时，Arial/Times 会被判给更宽的 DejaVu，页图文字折行、互相压字。
    这种错图看起来像「内容写错了」，报错反而好定位，所以校验不过直接失败。
    """
    missing = [name for name in ("soffice", "pdftoppm") if not shutil.which(name)]
    if missing:
        raise RuntimeError("生成页图缺少工具：" + "、".join(missing))
    render.verify_font_environment()


@dataclass
class PageImagesResult:
    """一次出图的结果汇总（也作为返回值写进 `core.background_jobs.result`）。"""

    total: int = 0
    generated: int = 0
    skipped: int = 0
    source_version: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "generated": self.generated,
            "skipped": self.skipped,
            "source_version": self.source_version,
        }


# ── 内容寻址 key ────────────────────────────────────────────────────────────


def source_pdf_key(source_sha256: str) -> str:
    """源 PPT 转出的 PDF 缓存路径（按「渲染管线指纹 + 源文件指纹」寻址）。

    带上 `RENDERER_KEY` 的原因：字体或转换参数一变，同一份源 PPT 转出来的画面就不同。
    如果仍只按源 sha 寻址，改完字体会继续命中旧 PDF，表现为「改了但没生效」。
    旧版本的 PDF 对象留在原前缀下不再被引用，交由人工清理，不在代码里做删除。
    """
    return f"ppt-video/pdf/{render.RENDERER_KEY}/{source_sha256}.pdf"


# ── 页图产物（渲染任务与出图任务共用） ──────────────────────────────────────


def page_images_fresh(project: PptVideoProject, slides: list[PptVideoSlide]) -> bool:
    """页图是否已与当前源版本、当前渲染管线一致，可直接跳过整本转换。

    除源版本外还要比对 `page_images_renderer`：字体/管线一变，旧图虽然「存在」
    但画面是错的，必须重出。老项目该列为空串，天然视为过期。
    """
    if project.page_images_version != project.source_version:
        return False
    if (project.page_images_renderer or "") != render.RENDERER_KEY:
        return False
    return bool(slides) and all(slide.image_object_key and slide.image_sha256 for slide in slides)


def slide_assets_ready(project_id: uuid.UUID, slide: PptVideoSlide, image_sha: str) -> bool:
    """页图三份产物都在且画面指纹没变时跳过重传。"""
    from app.modules.agent import service as agent_service

    if slide.image_sha256 != image_sha:
        return False
    keys = (
        agent_service.slide_image_key(project_id, slide.slide_uid),
        agent_service.slide_preview_key(project_id, slide.slide_uid),
        agent_service.slide_thumb_key(project_id, slide.slide_uid),
    )
    return all(storage.stat_object(agent_service.BUCKET_MODULE, key) is not None for key in keys)


def publish_slide_images(
    project_id: uuid.UUID,
    slide: PptVideoSlide,
    image_path: Path,
    work_dir: Path,
) -> None:
    """页图三份产物一起落库。

    成片仍读原始 PNG（保证画质，也不让已缓存的视频片段失效），
    预览大图与缩略图是派生 JPEG，体积只有原图的 1/10 左右。

    三份产物的编码与上传彼此独立，串起来做纯属排队等待：并发提交后
    单页耗时从「3 次上传 + 2 次编码之和」降到「最慢的那一份」。
    minio-py 基于 urllib3 连接池，线程安全，可以直接并发。
    """
    from app.modules.agent import service as agent_service

    bucket = agent_service.BUCKET_MODULE

    def _upload_preview() -> None:
        preview_path = render.encode_jpeg(
            image_path,
            work_dir / "preview" / f"{slide.slide_uid}.jpg",
            render.PREVIEW_MAX_WIDTH,
            render.PREVIEW_JPEG_QUALITY,
        )
        storage.upload_file(
            bucket, agent_service.slide_preview_key(project_id, slide.slide_uid), str(preview_path), "image/jpeg"
        )

    def _upload_thumb() -> None:
        thumb_path = render.encode_jpeg(
            image_path,
            work_dir / "thumb" / f"{slide.slide_uid}.jpg",
            render.THUMB_WIDTH,
            render.THUMB_JPEG_QUALITY,
        )
        storage.upload_file(
            bucket, agent_service.slide_thumb_key(project_id, slide.slide_uid), str(thumb_path), "image/jpeg"
        )

    def _upload_original() -> None:
        storage.upload_file(
            bucket, agent_service.slide_image_key(project_id, slide.slide_uid), str(image_path), "image/png"
        )

    with ThreadPoolExecutor(max_workers=3, thread_name_prefix="ppt-page-upload") as pool:
        futures = [pool.submit(_upload_original), pool.submit(_upload_preview), pool.submit(_upload_thumb)]
        for future in futures:
            # 任一产物失败都算这一页失败：缺缩略图会让列表空白，缺原图会让成片读不到
            future.result()


def download_slide_images(project_id: uuid.UUID, slides: list[PptVideoSlide], target_dir: Path) -> list[Path]:
    """按「源 PPT 页序」把已生成的页图下载到本地，供渲染复用。

    渲染循环用 `source_index` 取图，换源后 slide_no 与源页序不再相同，
    所以必须按 source_index 归位，不能按数据库返回顺序：

    下载后重算指纹，与库里记的不一致说明缓存被污染，抛异常让调用方回退到重新转换，
    宁可多转一次，也不能把错的画面渲染进成片。
    """
    from app.modules.agent import service as agent_service

    target_dir.mkdir(parents=True, exist_ok=True)
    paths: list[Path | None] = [None] * len(slides)
    for slide in slides:
        index = (slide.source_index or slide.slide_no) - 1
        if index < 0 or index >= len(slides):
            raise RuntimeError(f"第 {slide.slide_no} 页在源 PPT 中没有对应位置")
        if not slide.image_object_key:
            raise RuntimeError(f"第 {slide.slide_no} 页缺少页图")
        payload = storage.get_object(agent_service.BUCKET_MODULE, slide.image_object_key)
        if payload is None:
            raise RuntimeError(f"第 {slide.slide_no} 页图已丢失")
        data, _content_type = payload
        if slide.image_sha256 and sha256_bytes(data) != slide.image_sha256:
            raise RuntimeError(f"第 {slide.slide_no} 页图指纹不匹配")
        path = target_dir / f"slide-{index + 1:04d}.png"
        path.write_bytes(data)
        paths[index] = path
    if any(path is None for path in paths):
        raise RuntimeError("页图页序不完整，无法复用")
    return [path for path in paths if path is not None]


def ensure_source_pdf(source_sha256: str, source_path: Path, work_dir: Path) -> Path:
    """取源 PDF：优先命中内容寻址缓存，未命中才跑 soffice。

    LibreOffice 是整文件级转换，慢且吃 CPU，是整个链路里最贵的一步；
    命中缓存后，改一页重渲只剩拆图与编码。
    """
    from app.modules.agent import service as agent_service

    cache_key = source_pdf_key(source_sha256)
    target = work_dir / "pdf" / "source.pdf"
    payload = storage.get_object(agent_service.BUCKET_MODULE, cache_key)
    if payload is not None:
        data, _content_type = payload
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        logger.info("命中源 PDF 缓存: %s", cache_key)
        return target

    pdf_path = render.pptx_to_pdf(source_path, work_dir / "pdf", work_dir / "lo-profile")
    storage.upload_file(agent_service.BUCKET_MODULE, cache_key, str(pdf_path), "application/pdf")
    return pdf_path


# ── 后台任务 ────────────────────────────────────────────────────────────────


async def _wait_project(project_id: uuid.UUID, expect_version: int = 0) -> PptVideoProject | None:
    """等主事务提交、且源版本推进到 `expect_version` 后再读，最多等 `PROJECT_WAIT_SECONDS`。

    换源是「先改库、后投递」：任务被调度时主事务可能还没提交，
    这时读到的是旧 `source_version`，直接出图会白转一次旧源。
    """
    deadline = time.monotonic() + PROJECT_WAIT_SECONDS
    while True:
        async with async_session_factory() as session:
            project = await session.scalar(
                select(PptVideoProject).where(PptVideoProject.id == project_id, PptVideoProject.is_deleted.is_(False))
            )
            if project is not None and project.source_version >= expect_version:
                return project
        if time.monotonic() >= deadline:
            return None
        await asyncio.sleep(PROJECT_WAIT_INTERVAL_SECONDS)


async def _set_state(project_id: uuid.UUID, job_id: uuid.UUID | None = None, **values: Any) -> None:
    """把页图进度写到项目行（独立会话，不加入调用方事务）。

    两个关键点：
    - **独立会话 + 单条 UPDATE**：出图是几十秒到几分钟的长任务，
      不能把项目行锁在别的事务里等它出完。
    - **带 `page_images_job_id` 条件**：连续保存会排多个任务，
      旧任务收尾时不能覆盖新任务写下的状态，否则进度条会倒退或卡住。
    进度是辅助信息，写失败只记日志、不让出图失败。
    """
    conditions = [PptVideoProject.id == project_id]
    if job_id is not None:
        conditions.append(PptVideoProject.page_images_job_id == job_id)
    try:
        async with async_session_factory() as session:
            await session.execute(update(PptVideoProject).where(*conditions).values(**values))
            await session.commit()
    except Exception:  # noqa: BLE001 - 进度写失败不影响出图结果
        logger.exception("页图进度写入失败: project=%s", project_id)


async def _claim(project_id: uuid.UUID, job_id: uuid.UUID | None, total: int) -> None:
    """认领任务：无条件把 `job_id` 写到项目行，并把状态置为 running。

    `_set_state` 的进度写入都带 `page_images_job_id == job_id` 条件，**只有认领之后才会命中**。
    短路径（没有源、已是最新、没有页面）也必须先认领再写结论，否则它们的 UPDATE 会静默匹配
    0 行、状态停在上一次的值（曾导致「已是最新」分支永远不显示完成）。
    """
    await _set_state(
        project_id,
        page_images_job_id=job_id,
        page_images_status=PAGE_IMAGES_STATUS_RUNNING,
        page_images_progress=0,
        page_images_done=0,
        page_images_total=total,
        page_images_error=None,
    )


def _lerp_progress(index: int, total: int, start: int, end: int) -> int:
    """把「第 index / 共 total」映射到 [start, end] 区间。"""
    if total <= 0:
        return end
    return min(end, start + round((end - start) * index / total))


def _short_error(exc: BaseException) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    return text[:500]


async def _load_slides(session: AsyncSession, project_id: uuid.UUID) -> list[PptVideoSlide]:
    result = await session.scalars(
        select(PptVideoSlide)
        .where(PptVideoSlide.project_id == project_id, PptVideoSlide.is_deleted.is_(False))
        .order_by(PptVideoSlide.slide_no)
    )
    return list(result)


def _download_source(object_key: str, work_dir: Path) -> Path:
    from app.modules.agent import service as agent_service

    payload = storage.get_object(agent_service.BUCKET_MODULE, object_key)
    if payload is None:
        raise RuntimeError("源 PPT 已丢失，无法生成页图")
    data, _content_type = payload
    path = work_dir / "source.pptx"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return path


async def _commit(
    project_id: uuid.UUID,
    source_version: int,
    published: list[tuple[uuid.UUID, str]],
    total: int,
    job_id: uuid.UUID | None = None,
) -> PageImagesResult:
    """把本次出图结果写回库；源已换版本或任务已被新任务取代就整批丢弃。"""
    from app.modules.agent import service as agent_service

    async with async_session_factory() as session:
        # 行锁：收尾这一刻可能已有新任务在写状态，锁住再判断，避免 check-then-write 的竞态
        project = await session.get(PptVideoProject, project_id, with_for_update=True)
        if project is None or project.is_deleted:
            logger.info("页图任务跳过：项目已删除 %s", project_id)
            return PageImagesResult(total=total, skipped=total)
        if job_id is not None and project.page_images_job_id != job_id:
            logger.info("页图任务放弃提交：已被新任务取代 %s", project_id)
            return PageImagesResult(total=total, skipped=total, source_version=source_version)
        if project.source_version != source_version:
            logger.info("页图任务丢弃：源已从 v%s 更新，%s", source_version, project_id)
            # 画面已不属于当前源：清掉状态，避免前端一直转圈；新任务的 running 会覆盖它
            project.page_images_status = PAGE_IMAGES_STATUS_IDLE
            project.page_images_progress = 0
            project.page_images_error = None
            await session.commit()
            return PageImagesResult(total=total, skipped=total, source_version=source_version)

        for slide_uid, image_sha in published:
            await session.execute(
                update(PptVideoSlide)
                .where(PptVideoSlide.project_id == project_id, PptVideoSlide.slide_uid == slide_uid)
                .values(
                    image_object_key=agent_service.slide_image_key(project_id, slide_uid),
                    image_sha256=image_sha,
                )
            )
        project.page_images_version = source_version
        project.page_images_renderer = render.RENDERER_KEY
        project.page_images_status = PAGE_IMAGES_STATUS_DONE
        project.page_images_progress = 100
        project.page_images_done = total
        project.page_images_total = total
        project.page_images_error = None
        await session.commit()

    return PageImagesResult(
        total=total,
        generated=len(published),
        skipped=total - len(published),
        source_version=source_version,
    )


async def run_for_project(
    project_id: uuid.UUID,
    expect_version: int = 0,
    force: bool = False,
    job_id: uuid.UUID | None = None,
) -> dict[str, Any]:
    """生成（或补齐）项目全部页图，并把进度写到项目行。"""
    project = await _wait_project(project_id, expect_version)
    if project is None:
        return {"status": "skipped", "reason": "项目不可见"}
    if not project.source_object_key:
        await _claim(project_id, job_id, 0)
        await _set_state(
            project_id,
            job_id,
            page_images_status=PAGE_IMAGES_STATUS_IDLE,
            page_images_progress=0,
            page_images_total=0,
            page_images_error="项目没有源 PPT",
        )
        return {"status": "skipped", "reason": "项目没有源 PPT"}

    async with async_session_factory() as session:
        slides = await _load_slides(session, project_id)
    slide_total = len(slides)
    if not slides:
        await _claim(project_id, job_id, 0)
        await _set_state(
            project_id,
            job_id,
            page_images_status=PAGE_IMAGES_STATUS_IDLE,
            page_images_progress=0,
            page_images_total=0,
            page_images_error="项目没有页面",
        )
        return {"status": "skipped", "reason": "项目没有页面"}
    if not force and page_images_fresh(project, slides):
        # 连续编辑会连着投递多个任务，前一个已经出完图时没必要再转一遍；
        # 但仍要把状态置为「完成」，否则前端会一直停在「排队中」
        logger.info("页图已是最新，跳过: project=%s v%s", project_id, project.source_version)
        await _claim(project_id, job_id, slide_total)
        await _set_state(
            project_id,
            job_id,
            page_images_status=PAGE_IMAGES_STATUS_DONE,
            page_images_progress=100,
            page_images_done=slide_total,
            page_images_total=slide_total,
            page_images_error=None,
        )
        return {"status": "skipped", "reason": "页图已是最新", "total": slide_total, "skipped": slide_total}

    # 快照：出图期间源可能被换掉，写回时用这个版本号做条件
    source_version = project.source_version
    source_key = project.source_object_key
    source_sha256 = project.source_sha256

    settings = await load_settings()

    # 认领任务：从这里开始，本任务的进度写入才能落到这一行（旧任务会在 _set_state 里被条件挡掉）
    await _claim(project_id, job_id, slide_total)

    # 工具/字体自检放在认领之后：它抛错时，失败状态才带得上 job_id 写回这一行，
    # 否则用户只看到进度条停在「排队中」，看不到失败原因。
    _ensure_page_image_tools()

    work_dir = Path(tempfile.mkdtemp(prefix=f"ppt-pages-{project_id.hex[:8]}-"))
    try:
        async with _CONVERSION_SLOT:
            source_path = await asyncio.to_thread(_download_source, source_key, work_dir)
            pdf_path = await asyncio.to_thread(ensure_source_pdf, source_sha256, source_path, work_dir)
            await _set_state(project_id, job_id, page_images_progress=PROGRESS_CONVERT_END)

            # 分批拆图：一批一次 pdftoppm，每批结束报一次进度，
            # 用户仍能看见「正在拆第 n 页」，而进程次数从「每页一次」降到「每批一次」
            pdf_pages = await asyncio.to_thread(render.pdf_page_count, pdf_path)
            images: list[Path] = []
            batch_size = max(1, settings.pdf_split_batch)
            for start in range(1, pdf_pages + 1, batch_size):
                end = min(pdf_pages, start + batch_size - 1)
                images.extend(
                    await asyncio.to_thread(
                        render.render_pdf_page_batch, pdf_path, work_dir / "png", start, end, settings.render_dpi
                    )
                )
                await _set_state(
                    project_id,
                    job_id,
                    page_images_progress=_lerp_progress(
                        len(images), pdf_pages, PROGRESS_SPLIT_START, PROGRESS_SPLIT_END
                    ),
                    page_images_done=min(len(images), slide_total),
                )
        if len(images) != slide_total:
            logger.warning(
                "页图任务跳过：出图 %s 页与库里 %s 页不一致 project=%s",
                len(images),
                slide_total,
                project_id,
            )
            await _set_state(
                project_id,
                job_id,
                page_images_status=PAGE_IMAGES_STATUS_FAILED,
                page_images_error=f"页数不一致：图 {len(images)} / 页 {slide_total}",
            )
            return {"status": "skipped", "reason": f"页数不一致：图 {len(images)} / 页 {slide_total}"}

        published: list[tuple[uuid.UUID, str]] = []
        processed = 0
        # 上传是网络等待：并发出去，但进度仍按原顺序逐页推进，保证百分比单调
        upload_concurrency = max(1, min(settings.page_concurrency, 3))

        async def _publish_one(slide: PptVideoSlide, image_path: Path) -> tuple[str, bool]:
            image_sha = await asyncio.to_thread(sha256_file, image_path)
            if slide.image_sha256 == image_sha and await asyncio.to_thread(
                slide_assets_ready, project_id, slide, image_sha
            ):
                return image_sha, False
            await asyncio.to_thread(publish_slide_images, project_id, slide, image_path, work_dir)
            return image_sha, True

        pairs = list(zip(slides, images, strict=True))
        for start in range(0, len(pairs), upload_concurrency):
            chunk = pairs[start : start + upload_concurrency]
            outcomes = await asyncio.gather(*(_publish_one(slide, path) for slide, path in chunk))
            for (slide, _path), (image_sha, did_publish) in zip(chunk, outcomes, strict=True):
                if did_publish:
                    published.append((slide.slide_uid, image_sha))
                processed += 1
                # 只推进百分比、不回写 `page_images_done`：done 表示「已拆出的页数」，
                # 在拆图段就走到 total；上传段若改成「已上传页数」，前端会看到 53 → 1 的倒退
                # （实测 88% 时 done 从 53 掉到 11）。计数只增不减，收尾由 `_commit` 落 total。
                await _set_state(
                    project_id,
                    job_id,
                    page_images_progress=_lerp_progress(
                        processed, slide_total, PROGRESS_UPLOAD_START, PROGRESS_UPLOAD_END
                    ),
                )
    finally:
        await asyncio.to_thread(shutil.rmtree, work_dir, True)

    result = await _commit(project_id, source_version, published, slide_total, job_id=job_id)
    logger.info("页图任务完成: %s", result.as_dict())
    return {"status": "done", **result.as_dict()}


async def submit(project_id: uuid.UUID, expect_version: int = 0, force: bool = False) -> uuid.UUID | None:
    """提交后台任务；登记失败只记日志，不影响上传/换源主流程。"""

    async def _run(job_id: uuid.UUID) -> dict[str, Any]:
        try:
            if not force:
                # 连续保存会连着投递：稍等一下让编辑停下，前面的任务就会命中「已是最新」短路
                await asyncio.sleep(PAGE_IMAGES_DEBOUNCE_SECONDS)
            return await run_for_project(project_id, expect_version, force, job_id=job_id)
        except Exception as exc:
            # 先给用户一个可读的失败原因，再把异常交给 core.jobs 记录与重试
            await _set_state(
                project_id,
                job_id,
                page_images_status=PAGE_IMAGES_STATUS_FAILED,
                page_images_error=_short_error(exc),
            )
            raise

    return await submit_job_safe(JOB_NAME, _run)
