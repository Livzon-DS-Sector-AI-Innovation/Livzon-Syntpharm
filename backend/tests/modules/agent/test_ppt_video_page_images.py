"""页图任务：缓存命中判定、源页序归位、中间 PDF 复用。

全部是纯函数或 mock 掉对象存储的用例，不需要数据库与 soffice。
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from app.core import storage
from app.modules.agent import page_images, render, service

PROJECT_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _slide(
    slide_no: int,
    *,
    source_index: int | None = None,
    image_key: str | None = "img/1",
    image_sha: str | None = "sha",
) -> Any:
    return SimpleNamespace(
        slide_no=slide_no,
        slide_uid=uuid.uuid4(),
        source_index=source_index if source_index is not None else slide_no,
        image_object_key=image_key,
        image_sha256=image_sha,
    )


def _project(
    *,
    source_version: int = 1,
    page_images_version: int = 1,
    page_images_renderer: str | None = render.RENDERER_KEY,
) -> Any:
    return SimpleNamespace(
        source_version=source_version,
        page_images_version=page_images_version,
        page_images_renderer=page_images_renderer,
    )


def test_source_pdf_key_is_content_addressed() -> None:
    # 同一份源 PPT 在不同项目里必须落到同一个 key，才能真正跨项目复用
    assert page_images.source_pdf_key("abc123") == page_images.source_pdf_key("abc123")
    assert page_images.source_pdf_key("abc123") != page_images.source_pdf_key("abc124")


def test_source_pdf_key_is_scoped_by_renderer() -> None:
    # 字体/拆图参数一变，同一份源 PPT 的 PDF 画面就不同，必须换 key 才能避免命中旧缓存
    key = page_images.source_pdf_key("abc123")
    assert render.RENDERER_KEY in key
    assert key == f"ppt-video/pdf/{render.RENDERER_KEY}/abc123.pdf"


def test_page_images_fresh_requires_matching_source_version() -> None:
    slides = [_slide(1), _slide(2)]

    assert page_images.page_images_fresh(_project(source_version=2, page_images_version=1), slides) is False
    assert page_images.page_images_fresh(_project(source_version=2, page_images_version=2), slides) is True


def test_page_images_fresh_rejects_old_renderer() -> None:
    # 老项目该列是空串：图还在，但字体是旧的，必须重出
    slides = [_slide(1), _slide(2)]

    assert page_images.page_images_fresh(_project(page_images_renderer=""), slides) is False
    assert page_images.page_images_fresh(_project(page_images_renderer="r1-legacy"), slides) is False


def test_lerp_progress_maps_page_index_into_segment() -> None:
    # 逐页上报：第 0 页停在段首，最后一页正好到段尾，不允许越界
    assert page_images._lerp_progress(0, 10, 40, 85) == 40
    assert page_images._lerp_progress(10, 10, 40, 85) == 85
    assert page_images._lerp_progress(99, 10, 40, 85) == 85
    assert page_images._lerp_progress(3, 0, 40, 85) == 85


def test_page_images_fresh_requires_every_slide_image() -> None:
    slides = [_slide(1), _slide(2, image_key=None)]

    assert page_images.page_images_fresh(_project(), slides) is False


def test_page_images_fresh_rejects_empty_project() -> None:
    assert page_images.page_images_fresh(_project(), []) is False


def test_download_slide_images_orders_by_source_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 换源后 slide_no 会被重排，渲染按 source_index 取图，下载也必须按源页序归位
    pages = [b"page-one", b"page-two", b"page-three"]
    slides = [
        _slide(1, source_index=3, image_key="img/1"),
        _slide(2, source_index=1, image_key="img/2"),
        _slide(3, source_index=2, image_key="img/3"),
    ]
    for slide, data in zip(slides, pages, strict=True):
        slide.image_sha256 = hashlib.sha256(data).hexdigest()
    stored = {f"img/{no}": (page, "image/png") for no, page in zip((1, 2, 3), pages, strict=True)}
    monkeypatch.setattr(storage, "get_object", lambda _module, key: stored.get(key))

    paths = page_images.download_slide_images(PROJECT_ID, slides, tmp_path)

    assert [path.read_bytes() for path in paths] == [pages[1], pages[2], pages[0]]


def test_download_slide_images_rejects_tampered_image(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    slide = _slide(1, image_key="img/1", image_sha=hashlib.sha256(b"expected").hexdigest())
    monkeypatch.setattr(storage, "get_object", lambda _module, _key: (b"tampered", "image/png"))

    with pytest.raises(RuntimeError, match="指纹不匹配"):
        page_images.download_slide_images(PROJECT_ID, [slide], tmp_path)


def test_ensure_source_pdf_prefers_cached_pdf(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cached = b"%PDF-1.7 cached"

    def _unexpected_conversion(*_args: object, **_kwargs: object) -> None:
        pytest.fail("命中缓存时不应再跑一次 soffice")

    monkeypatch.setattr(storage, "get_object", lambda _module, _key: (cached, "application/pdf"))
    monkeypatch.setattr(render, "pptx_to_pdf", _unexpected_conversion)

    path = page_images.ensure_source_pdf("abc123", tmp_path / "source.pptx", tmp_path)

    assert path.read_bytes() == cached


def test_ensure_source_pdf_converts_and_caches_on_miss(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    uploaded: list[tuple[str, str]] = []
    pdf_path = tmp_path / "pdf" / "source.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    pdf_path.write_bytes(b"%PDF-1.7 fresh")

    monkeypatch.setattr(storage, "get_object", lambda _module, _key: None)
    monkeypatch.setattr(render, "pptx_to_pdf", lambda *_args, **_kwargs: pdf_path)
    monkeypatch.setattr(
        storage,
        "upload_file",
        lambda _module, key, _path, content_type: uploaded.append((key, content_type)),
    )

    result = page_images.ensure_source_pdf("abc123", tmp_path / "source.pptx", tmp_path)

    assert result == pdf_path
    assert uploaded == [(page_images.source_pdf_key("abc123"), "application/pdf")]


def _state_project(**overrides: Any) -> Any:
    """`service.page_images_state` 只读项目列，用 SimpleNamespace 就够，不必建库。"""
    data: dict[str, Any] = {
        "source_version": 2,
        "page_images_version": 2,
        "page_images_renderer": render.RENDERER_KEY,
        "page_images_status": "idle",
        "page_images_progress": 0,
        "page_images_done": 0,
        "page_images_total": 0,
        "page_images_error": None,
        "page_images_job_id": None,
        "slide_count": 5,
        "updated_at": datetime.now(UTC),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_page_images_state_reports_done_for_up_to_date_project() -> None:
    # 老项目升级后状态列还是 idle，但版本与指纹都对得上：直接呈现完成，别让用户重出图
    state = service.page_images_state(_state_project())

    assert (state.status, state.progress, state.done, state.total) == ("done", 100, 5, 5)


def test_page_images_state_keeps_running_when_versions_already_match() -> None:
    # 强制重试一个内容已最新的项目：状态列是 running，不能被「版本一致」改写成 done，
    # 否则进度条一出现就消失（前端看到终态就停止轮询）
    project = _state_project(
        page_images_status="running",
        page_images_progress=40,
        page_images_done=2,
        page_images_total=5,
        page_images_job_id=uuid.uuid4(),
    )

    state = service.page_images_state(project)

    assert state.status == "running"
    assert state.progress == 40


def test_page_images_state_keeps_failure_reason_when_versions_match() -> None:
    # 页数校验失败的场景：源版本没变，但状态是 failed，错误原因必须透出来
    project = _state_project(page_images_status="failed", page_images_progress=70, page_images_error="页图页数不一致")

    state = service.page_images_state(project)

    assert state.status == "failed"
    assert state.error == "页图页数不一致"


def test_page_images_state_marks_stale_running_as_failed() -> None:
    # 进程被杀后状态会永远停在 running，前端会无限轮询：超时按失败呈现并给出重试理由
    project = _state_project(
        page_images_status="running",
        page_images_progress=80,
        updated_at=datetime.now(UTC) - timedelta(seconds=service.PAGE_IMAGES_STALE_SECONDS + 60),
    )

    state = service.page_images_state(project)

    assert state.status == "failed"
    assert state.error is not None


def test_page_images_state_ignores_stale_renderer() -> None:
    # 版本号一致但指纹是旧的：图还在，画面已经不对，不能呈现为完成
    state = service.page_images_state(_state_project(page_images_renderer="r1-legacy"))

    assert state.status == "idle"


def test_page_images_state_keeps_queued_when_versions_already_match() -> None:
    # 上传/换源时先落 queued 再投递，前端靠它显示进度条并开始轮询；
    # 此时版本号可能还没变（强制重跑），不能被「版本一致」改写成 done
    project = _state_project(page_images_status="queued", page_images_total=5)

    state = service.page_images_state(project)

    assert state.status == "queued"
    assert state.progress == 0


def test_mark_page_images_queued_resets_progress_and_error() -> None:
    project: Any = SimpleNamespace(
        page_images_status="failed",
        page_images_progress=90,
        page_images_done=4,
        page_images_total=5,
        page_images_error="soffice 挂了",
        slide_count=6,
    )

    service.mark_page_images_queued(project)

    assert project.page_images_status == "queued"
    assert (project.page_images_progress, project.page_images_done, project.page_images_total) == (0, 0, 6)
    assert project.page_images_error is None


def test_page_images_state_marks_stale_queued_as_failed() -> None:
    # 投递成功但任务始终没被认领：进度条不能永远停在「排队中」
    project = _state_project(
        page_images_status="queued",
        updated_at=datetime.now(UTC) - timedelta(seconds=service.PAGE_IMAGES_QUEUE_STALE_SECONDS + 30),
    )

    state = service.page_images_state(project)

    assert state.status == "failed"
    assert state.error is not None


async def test_progress_done_never_regresses_across_upload_phase(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`page_images_done` 只增不减。

    拆图段会一路推进到总页数；上传段若再按「已上传页数」回写，前端会看到
    53 → 1 的倒退（2026-11-03 真机实测 88% 时 done 从 53 掉到 11）。
    """
    slides = [_slide(no) for no in (1, 2, 3)]
    states: list[dict[str, Any]] = []

    async def _fake_set_state(project_id: uuid.UUID, job_id: uuid.UUID | None = None, **values: Any) -> None:
        states.append(values)

    async def _fake_wait_project(project_id: uuid.UUID, expect_version: int = 0) -> Any:
        return SimpleNamespace(source_object_key="src.pptx", source_sha256="sha", source_version=1)

    async def _fake_load_slides(session: Any, project_id: uuid.UUID) -> list[Any]:
        return slides

    async def _fake_settings() -> Any:
        return SimpleNamespace(render_dpi=150, pdf_split_batch=2, page_concurrency=2)

    async def _fake_commit(
        project_id: uuid.UUID,
        source_version: int,
        published: list[tuple[uuid.UUID, str]],
        total: int,
        job_id: uuid.UUID | None = None,
    ) -> Any:
        return page_images.PageImagesResult(total=total, generated=len(published), source_version=source_version)

    monkeypatch.setattr(page_images, "_set_state", _fake_set_state)
    monkeypatch.setattr(page_images, "_wait_project", _fake_wait_project)
    monkeypatch.setattr(page_images, "_load_slides", _fake_load_slides)
    monkeypatch.setattr(page_images, "load_settings", _fake_settings)
    monkeypatch.setattr(page_images, "_ensure_page_image_tools", lambda: None)
    monkeypatch.setattr(page_images, "_download_source", lambda key, work_dir: tmp_path / "source.pptx")
    monkeypatch.setattr(page_images, "ensure_source_pdf", lambda sha, path, work_dir: tmp_path / "source.pdf")
    monkeypatch.setattr(render, "pdf_page_count", lambda path: 3)
    monkeypatch.setattr(
        render,
        "render_pdf_page_batch",
        lambda pdf, out_dir, first, last, dpi=150: [tmp_path / f"p{page}.png" for page in range(first, last + 1)],
    )
    monkeypatch.setattr(page_images, "sha256_file", lambda path: f"sha-{Path(path).stem}")
    monkeypatch.setattr(page_images, "slide_assets_ready", lambda project_id, slide, sha: False)
    monkeypatch.setattr(page_images, "publish_slide_images", lambda *args, **kwargs: None)
    monkeypatch.setattr(page_images, "_commit", _fake_commit)

    result = await page_images.run_for_project(PROJECT_ID, force=True)

    assert result["status"] == "done"
    done = [values["page_images_done"] for values in states if "page_images_done" in values]
    assert done == sorted(done), f"done 出现倒退: {done}"
    assert done[-1] == 3
    # 上传段（进度 > 85）只推进百分比，不再回写计数
    upload_states = [values for values in states if values.get("page_images_progress", 0) > 85]
    assert upload_states
    assert all("page_images_done" not in values for values in upload_states)
