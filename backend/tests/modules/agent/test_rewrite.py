"""讲稿改写编排单测：目标页选择、快照写入、失败分级与回滚。

依赖数据库（需先 `alembic upgrade head`）；模型调用用 monkeypatch 替换
`rewrite.llm_client.chat_json` 与 `rewrite.resolve`，不连真实 LLM。
"""

import uuid
from dataclasses import replace

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import LLMProviderError
from app.modules.agent import rewrite
from app.modules.agent.ai_config import ResolvedModel
from app.modules.agent.config import DEFAULTS
from app.modules.agent.models import (
    REVISION_STATUS_FAILED,
    REVISION_STATUS_SUCCEEDED,
    REWRITE_MODE_FILL_BLANK,
    REWRITE_MODE_REWRITE_ALL,
    REWRITE_MODE_REWRITE_ONE,
    REWRITE_MODE_REWRITE_SELECTED,
    SCRIPT_AI_STATUS_DONE,
    SCRIPT_AI_STATUS_FAILED,
    SCRIPT_AI_STATUS_PARTIAL,
    SCRIPT_SOURCE_AI,
    SCRIPT_SOURCE_UPLOAD,
    PptVideoProject,
    PptVideoScriptRevision,
    PptVideoSlide,
)

SETTINGS = replace(DEFAULTS, script_ai_batch_size=2, script_ai_timeout_seconds=5)


def _model() -> ResolvedModel:
    return ResolvedModel(config_id=None, model_name="unit-test-model", provider="http://unit.test", source="env")


@pytest.fixture(autouse=True)
def _stub_resolve(monkeypatch: pytest.MonkeyPatch) -> None:
    """改写只关心「用哪个模型」，模型解析本身由 test_ai_config 覆盖。"""

    async def fake_resolve(*_args, **_kwargs) -> ResolvedModel:
        return _model()

    monkeypatch.setattr(rewrite, "resolve", fake_resolve)


async def _make_project(session: AsyncSession) -> PptVideoProject:
    project = PptVideoProject(
        id=uuid.uuid4(),
        name=f"改写测试-{uuid.uuid4().hex[:6]}",
        source_object_key=f"agent/ppt-video/source/{uuid.uuid4().hex}.pptx",
        source_filename="deck.pptx",
        source_sha256=uuid.uuid4().hex * 2,
        slide_count=3,
        default_language="zh",
        default_voice_id="zf_001",
        speed=1.0,
    )
    session.add(project)
    await session.flush()
    return project


async def _add_slide(
    session: AsyncSession,
    project: PptVideoProject,
    slide_no: int,
    *,
    text: str | None,
    script: str = "",
    source: str = "",
    notes: str | None = None,
    audio_key: str | None = None,
) -> PptVideoSlide:
    slide = PptVideoSlide(
        id=uuid.uuid4(),
        project_id=project.id,
        slide_no=slide_no,
        script_text=script,
        script_source=source,
        page_text=text,
        page_notes=notes,
        audio_object_key=audio_key,
        audio_sha256="f" * 64 if audio_key else None,
        duration_ms=3000 if audio_key else 0,
    )
    session.add(slide)
    await session.flush()
    return slide


def _fake_llm(monkeypatch: pytest.MonkeyPatch, scripts: dict[int, str], seen: list[list[dict]] | None = None):
    async def fake_chat_json(messages, expected_keys=None, **kwargs):
        if seen is not None:
            seen.append(messages)
        return {"slides": [{"slide_no": no, "script": text} for no, text in scripts.items()]}

    monkeypatch.setattr(rewrite.llm_client, "chat_json", fake_chat_json)


def _raise_on_nth(monkeypatch: pytest.MonkeyPatch, fail_at: int):
    calls = {"count": 0}

    async def fake_chat_json(messages, expected_keys=None, **kwargs):
        calls["count"] += 1
        if calls["count"] == fail_at:
            raise LLMProviderError("上游 502")
        return {"slides": []}

    monkeypatch.setattr(rewrite.llm_client, "chat_json", fake_chat_json)


# ── 目标页选择 ────────────────────────────────────────────────────────────


async def test_select_targets_fill_blank_only_picks_blank(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    await _add_slide(db_session, project, 1, text="第一页", script="上传稿", source=SCRIPT_SOURCE_UPLOAD)
    await _add_slide(db_session, project, 2, text="第二页有字")
    await _add_slide(db_session, project, 3, text=None, notes=None)

    slides = sorted(await _slides(db_session, project), key=lambda item: item.slide_no)
    targets, skipped = rewrite._select_targets(slides, rewrite.RewriteRequest(mode=REWRITE_MODE_FILL_BLANK))

    assert [slide.slide_no for slide in targets] == [2]
    assert skipped == 1  # 第 3 页无文字无备注，跳过不算失败


async def _slides(session: AsyncSession, project: PptVideoProject) -> list[PptVideoSlide]:
    result = await session.scalars(select(PptVideoSlide).where(PptVideoSlide.project_id == project.id))
    return list(result.all())


async def test_select_targets_rewrite_all_covers_every_generatable_page(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    await _add_slide(db_session, project, 1, text="第一页", script="已有稿")
    await _add_slide(db_session, project, 2, text=None, notes="只有备注也算可生成")
    await _add_slide(db_session, project, 3, text=None, notes=None)

    slides = sorted(await _slides(db_session, project), key=lambda item: item.slide_no)
    targets, skipped = rewrite._select_targets(slides, rewrite.RewriteRequest(mode=REWRITE_MODE_REWRITE_ALL))

    assert [slide.slide_no for slide in targets] == [1, 2]
    assert skipped == 1


async def test_select_targets_selected_and_one_modes_use_uid(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    first = await _add_slide(db_session, project, 1, text="第一页")
    await _add_slide(db_session, project, 2, text="第二页")

    slides = sorted(await _slides(db_session, project), key=lambda item: item.slide_no)
    for mode in (REWRITE_MODE_REWRITE_SELECTED, REWRITE_MODE_REWRITE_ONE):
        targets, _ = rewrite._select_targets(
            slides, rewrite.RewriteRequest(mode=mode, slide_uids=[str(first.slide_uid)])
        )
        assert [slide.slide_no for slide in targets] == [1]


# ── 执行 ──────────────────────────────────────────────────────────────────


async def test_run_writes_script_and_keeps_before_snapshot(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session)
    slide = await _add_slide(
        db_session,
        project,
        1,
        text="含量测定方法",
        script="旧的讲稿内容",
        source=SCRIPT_SOURCE_UPLOAD,
        audio_key="agent/ppt-video/audio/old.wav",
    )
    slide.script_stale = True
    await db_session.flush()

    seen: list[list[dict]] = []
    _fake_llm(monkeypatch, {1: "新的讲稿内容"}, seen)

    result = await rewrite.run(
        db_session,
        project,
        rewrite.RewriteRequest(
            mode=REWRITE_MODE_REWRITE_SELECTED,
            slide_uids=[str(slide.slide_uid)],
            instruction="更口语一点",
            requested_by_name="张三",
        ),
        SETTINGS,
    )

    assert result.status == SCRIPT_AI_STATUS_DONE
    assert result.total == 1 and result.done == 1 and result.failed == 0
    assert result.revision_id is not None

    refreshed = await db_session.get(PptVideoSlide, slide.id)
    await db_session.refresh(refreshed)
    assert refreshed.script_text == "新的讲稿内容"
    assert refreshed.script_source == SCRIPT_SOURCE_AI
    assert refreshed.script_stale is False
    # 讲稿变了就必须让旧音频失效，否则成片还是旧的旁白
    assert refreshed.audio_object_key is None
    assert refreshed.audio_sha256 is None
    assert refreshed.duration_ms == 0

    revision = await db_session.get(PptVideoScriptRevision, result.revision_id)
    assert revision is not None
    assert revision.applied is True
    assert revision.status == REVISION_STATUS_SUCCEEDED
    assert revision.before == {str(slide.slide_uid): "旧的讲稿内容"}
    assert revision.after == {str(slide.slide_uid): "新的讲稿内容"}
    assert revision.model_name == _model().model_name
    assert revision.requested_by_name == "张三"
    assert revision.instruction == "更口语一点"

    # 三层规则：单次指令必须真的进到 prompt 里
    assert "本次额外指令" in seen[0][1]["content"]
    assert "更口语一点" in seen[0][1]["content"]


async def test_run_partial_when_one_batch_fails(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session)
    await _add_slide(db_session, project, 1, text="第一页")
    await _add_slide(db_session, project, 2, text="第二页")

    calls = {"count": 0}

    async def fake_chat_json(messages, expected_keys=None, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"slides": [{"slide_no": 1, "script": "第一页新稿"}]}
        raise LLMProviderError("上游 502")

    monkeypatch.setattr(rewrite.llm_client, "chat_json", fake_chat_json)

    # 每批 1 页，才能只让第二批失败
    result = await rewrite.run(
        db_session,
        project,
        rewrite.RewriteRequest(mode=REWRITE_MODE_REWRITE_ALL),
        replace(SETTINGS, script_ai_batch_size=1),
    )

    assert result.status == SCRIPT_AI_STATUS_PARTIAL
    assert result.done == 1 and result.failed == 1
    assert result.errors and "第 2 页" in result.errors[0]

    revision = await db_session.get(PptVideoScriptRevision, result.revision_id)
    assert revision is not None
    # 有成功页就算 partial，修订记录按成功处理，允许回滚
    assert revision.status == REVISION_STATUS_SUCCEEDED


async def test_run_marks_failed_when_all_batches_fail(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session)
    await _add_slide(db_session, project, 1, text="第一页")

    _raise_on_nth(monkeypatch, fail_at=1)

    result = await rewrite.run(
        db_session, project, rewrite.RewriteRequest(mode=REWRITE_MODE_REWRITE_ALL), SETTINGS
    )

    assert result.status == SCRIPT_AI_STATUS_FAILED
    revision = await db_session.get(PptVideoScriptRevision, result.revision_id)
    assert revision is not None
    assert revision.status == REVISION_STATUS_FAILED
    assert revision.error_message

    refreshed = await db_session.get(PptVideoProject, project.id)
    await db_session.refresh(refreshed)
    assert refreshed.script_ai_status == SCRIPT_AI_STATUS_FAILED


async def test_run_without_targets_finishes_cleanly(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session)
    await _add_slide(db_session, project, 1, text="第一页", script="已有稿")

    _fake_llm(monkeypatch, {})

    result = await rewrite.run(
        db_session, project, rewrite.RewriteRequest(mode=REWRITE_MODE_FILL_BLANK), SETTINGS
    )

    assert result.total == 0 and result.done == 0
    assert result.status == SCRIPT_AI_STATUS_DONE
    revision = await db_session.get(PptVideoScriptRevision, result.revision_id)
    assert revision is not None and revision.status == REVISION_STATUS_SUCCEEDED


async def test_run_ignores_pages_outside_allowed_batch(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    """模型编造了范围外的页码时，不能写到别的页上。"""
    project = await _make_project(db_session)
    target = await _add_slide(db_session, project, 1, text="第一页")
    other = await _add_slide(db_session, project, 2, text="第二页", script="第二页原稿")

    _fake_llm(monkeypatch, {1: "第一页新稿", 2: "越界覆盖"})

    await rewrite.run(
        db_session,
        project,
        rewrite.RewriteRequest(mode=REWRITE_MODE_REWRITE_ONE, slide_uids=[str(target.slide_uid)]),
        SETTINGS,
    )

    # 只改第 1 页时模型顺手写了第 2 页，属于越界，必须丢弃
    refreshed = await db_session.get(PptVideoSlide, other.id)
    await db_session.refresh(refreshed)
    assert refreshed.script_text == "第二页原稿"


# ── 回滚 ──────────────────────────────────────────────────────────────────


async def _run_once(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> tuple[PptVideoProject, PptVideoSlide]:
    project = await _make_project(db_session)
    slide = await _add_slide(
        db_session, project, 1, text="第一页", script="人工稿", source=SCRIPT_SOURCE_UPLOAD, audio_key="a/b.wav"
    )
    _fake_llm(monkeypatch, {1: "AI 改写稿"})
    await rewrite.run(
        db_session,
        project,
        rewrite.RewriteRequest(mode=REWRITE_MODE_REWRITE_ONE, slide_uids=[str(slide.slide_uid)]),
        SETTINGS,
    )
    return project, slide


async def test_rollback_restores_before_and_marks_unapplied(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project, slide = await _run_once(db_session, monkeypatch)
    revision = await db_session.scalar(
        select(PptVideoScriptRevision).where(PptVideoScriptRevision.project_id == project.id)
    )
    assert revision is not None

    restored = await rewrite.rollback_revision(db_session, project.id, revision.id)

    assert restored == 1
    refreshed = await db_session.get(PptVideoSlide, slide.id)
    await db_session.refresh(refreshed)
    assert refreshed.script_text == "人工稿"
    assert refreshed.audio_object_key is None  # 回滚也要让旧音频失效

    await db_session.refresh(revision)
    assert revision.applied is False

    # 记录不删，只置为已回滚；重复回滚要明确报错
    with pytest.raises(ValueError):
        await rewrite.rollback_revision(db_session, project.id, revision.id)


async def test_rollback_unknown_revision_raises(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    with pytest.raises(ValueError):
        await rewrite.rollback_revision(db_session, project.id, uuid.uuid4())


async def test_list_revisions_newest_first(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session)
    slide = await _add_slide(db_session, project, 1, text="第一页", script="底稿")
    _fake_llm(monkeypatch, {1: "第一次改"})
    await rewrite.run(
        db_session,
        project,
        rewrite.RewriteRequest(mode=REWRITE_MODE_REWRITE_ONE, slide_uids=[str(slide.slide_uid)]),
        SETTINGS,
    )
    _fake_llm(monkeypatch, {1: "第二次改"})
    await rewrite.run(
        db_session,
        project,
        rewrite.RewriteRequest(mode=REWRITE_MODE_REWRITE_ONE, slide_uids=[str(slide.slide_uid)]),
        SETTINGS,
    )

    items = await rewrite.list_revisions(db_session, project.id)

    assert len(items) == 2
    assert items[0].created_at >= items[1].created_at
