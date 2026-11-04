"""AI 讲稿初稿单测：只填空页、跳过无文字页、部分失败、截断与防注入提示。

纯函数用例不依赖数据库；编排用例用 `db_session`（需先 `alembic upgrade head`），
模型调用用 monkeypatch 替换 `script_ai.llm_client.chat_json`，不连真实 LLM。
"""

import uuid
from dataclasses import replace
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import LLMProviderError, llm_client
from app.modules.agent import script_ai
from app.modules.agent.config import DEFAULTS, MAX_SCRIPT_CHARS
from app.modules.agent.models import (
    SCRIPT_AI_STATUS_DONE,
    SCRIPT_AI_STATUS_FAILED,
    SCRIPT_AI_STATUS_PARTIAL,
    SCRIPT_SOURCE_AI,
    SCRIPT_SOURCE_UPLOAD,
    PptVideoProject,
    PptVideoSlide,
)


def test_is_blank_script_treats_whitespace_as_empty() -> None:
    assert script_ai.is_blank_script(None)
    assert script_ai.is_blank_script("")
    assert script_ai.is_blank_script("  \n\t\u3000 ")
    assert not script_ai.is_blank_script(" 有内容 ")


def test_is_generatable_needs_text_or_notes() -> None:
    assert script_ai.is_generatable("页面文字", None)
    assert script_ai.is_generatable(None, "备注也算上下文")
    assert not script_ai.is_generatable("", "   ")
    assert not script_ai.is_generatable(None, None)


def test_extract_batch_scripts_drops_unknown_and_invalid() -> None:
    payload = {
        "slides": [
            {"slide_no": 1, "script": "  正文  "},
            {"slide_no": "2", "script": "字符串页码也要接受"},
            {"slide_no": 99, "script": "越界页码丢弃"},
            {"slide_no": 3, "script": "   "},
            {"slide_no": 4, "script": 123},
            {"slide_no": True, "script": "布尔值不是页码"},
            "不是对象",
        ]
    }

    scripts = script_ai.extract_batch_scripts(payload, {1, 2, 3, 4})

    assert scripts == {1: "正文", 2: "字符串页码也要接受"}


def test_extract_batch_scripts_caps_length() -> None:
    payload = {"slides": [{"slide_no": 1, "script": "字" * (MAX_SCRIPT_CHARS + 50)}]}
    scripts = script_ai.extract_batch_scripts(payload, {1})
    assert len(scripts[1]) == MAX_SCRIPT_CHARS


def test_extract_batch_scripts_handles_non_list() -> None:
    assert script_ai.extract_batch_scripts({"slides": {"slide_no": 1}}, {1}) == {}
    assert script_ai.extract_batch_scripts({}, {1}) == {}


# ── 段级讲稿与元素绑定 ─────────────────────────────────────────────────────


def test_normalize_segments_drops_unknown_and_duplicate_targets() -> None:
    segments = script_ai.normalize_segments(
        [
            {"text": " 收率提升 ", "targets": ["s0", "s0", "s99", "s1", "s2"]},
            {"text": "   "},
            "纯字符串段",
        ],
        {"s0", "s1"},
    )

    # 模型编出来的 id（s99）与非字符串一律丢弃；每段最多留两个目标
    assert segments == [
        {"text": "收率提升", "targets": ["s0", "s1"]},
        {"text": "纯字符串段", "targets": []},
    ]


def test_normalize_segments_caps_total_length() -> None:
    segments = script_ai.normalize_segments(
        [{"text": "字" * (MAX_SCRIPT_CHARS + 40), "targets": []}],
        set(),
    )
    assert len(segments_to_text(segments)) == MAX_SCRIPT_CHARS


def segments_to_text(segments: list[dict[str, Any]]) -> str:
    return "".join(segment["text"] for segment in segments)


def test_segments_to_script_joins_chinese_and_spaces_english() -> None:
    assert script_ai.segments_to_script([{"text": "第一句。"}, {"text": "第二句。"}]) == "第一句。第二句。"
    assert script_ai.segments_to_script([{"text": "First."}, {"text": "Second."}], "en") == "First. Second."


def test_extract_batch_segments_falls_back_to_legacy_script() -> None:
    payload = {
        "slides": [
            {"slide_no": 1, "script": "整页一段的旧格式"},
            {"slide_no": 2, "segments": [{"text": "新格式。", "targets": ["s0"]}]},
            {"slide_no": 3, "segments": []},
            {"slide_no": 99, "segments": [{"text": "越界", "targets": []}]},
        ]
    }

    result = script_ai.extract_batch_segments(payload, {1, 2, 3}, {2: {"s0"}})

    assert result[1] == [{"text": "整页一段的旧格式", "targets": []}]
    assert result[2] == [{"text": "新格式。", "targets": ["s0"]}]
    assert 3 not in result
    assert 99 not in result


def test_build_messages_lists_element_ids_for_targets() -> None:
    messages = script_ai.build_messages(
        "zh",
        "测试项目",
        [(1, "页面文字", None)],
        max_page_text_chars=500,
        element_catalogs={1: [{"id": "s0", "kind": "文本框", "text": "收率"}]},
    )

    prompt = messages[-1]["content"]
    assert "s0 [文本框] 收率" in prompt
    assert "targets" in prompt
    # 没有元素清单的页不应出现空清单标题
    empty = script_ai.build_messages("zh", "项目", [(1, "文字", None)], max_page_text_chars=500)
    assert "页面元素（targets 只能从这里取 id）" not in empty[-1]["content"]


def test_build_messages_truncates_and_marks_injection() -> None:
    messages = script_ai.build_messages(
        "zh",
        "测试项目",
        [(2, "甲" * 500, "备注内容")],
        max_page_text_chars=100,
    )

    assert messages[0]["role"] == "system"
    assert "忽略" in messages[0]["content"]
    user = messages[1]["content"]
    assert "幻灯片 2" in user
    assert "甲" * 100 in user
    assert "甲" * 101 not in user
    assert "备注内容" in user
    assert '"slides"' in user


def test_build_messages_falls_back_to_chinese() -> None:
    messages = script_ai.build_messages("fr", "Deck", [(1, "hello", None)], max_page_text_chars=100)
    assert "口播稿" in messages[0]["content"]


def test_batch_progress_keeps_100_for_finish() -> None:
    assert script_ai.batch_progress(0, 0) == 100
    assert script_ai.batch_progress(1, 3) == 33
    assert script_ai.batch_progress(3, 3) == 99


# ── 编排（依赖数据库） ─────────────────────────────────────────────────────


async def _make_project(session: AsyncSession) -> PptVideoProject:
    project = PptVideoProject(
        id=uuid.uuid4(),
        name=f"讲稿测试-{uuid.uuid4().hex[:6]}",
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


def _add_slide(
    session: AsyncSession,
    project: PptVideoProject,
    slide_no: int,
    *,
    text: str | None,
    notes: str | None = None,
    script: str = "",
    source: str = "",
) -> None:
    session.add(
        PptVideoSlide(
            id=uuid.uuid4(),
            project_id=project.id,
            slide_no=slide_no,
            script_text=script,
            script_source=source,
            page_text=text,
            page_notes=notes,
        )
    )


async def test_generate_only_fills_blank_pages(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    project = await _make_project(db_session)
    _add_slide(db_session, project, 1, text="第一页", script="上传的讲稿", source=SCRIPT_SOURCE_UPLOAD)
    _add_slide(db_session, project, 2, text="第二页文字，含 5 mg 剂量")
    _add_slide(db_session, project, 3, text=None, notes=None)
    await db_session.flush()

    seen: list[set[int]] = []

    async def fake_chat_json(messages: list[dict[str, str]], expected_keys: list[str] | None = None) -> dict[str, Any]:
        seen.append({1, 2})  # 记录调用次数用
        return {
            "slides": [
                {"slide_no": 1, "script": "不应覆盖上传稿"},
                {"slide_no": 2, "script": "第二页 AI 初稿"},
            ]
        }

    monkeypatch.setattr(llm_client, "chat_json", fake_chat_json)

    result = await script_ai.generate_for_project(db_session, project, replace(DEFAULTS, script_ai_batch_size=6))

    assert result.status == SCRIPT_AI_STATUS_DONE
    assert result.total == 1  # 只有第 2 页可生成
    assert result.done == 1
    assert result.skipped == 1
    assert len(seen) == 1

    slides = {
        slide.slide_no: slide
        for slide in (
            await db_session.scalars(select(PptVideoSlide).where(PptVideoSlide.project_id == project.id))
        ).all()
    }
    assert slides[1].script_text == "上传的讲稿"
    assert slides[1].script_source == SCRIPT_SOURCE_UPLOAD
    assert slides[2].script_text == "第二页 AI 初稿"
    assert slides[2].script_source == SCRIPT_SOURCE_AI
    assert slides[3].script_text == ""

    refreshed = await db_session.get(PptVideoProject, project.id)
    assert refreshed is not None
    assert refreshed.script_ai_status == SCRIPT_AI_STATUS_DONE
    assert refreshed.script_ai_progress == 100


async def test_generate_returns_done_when_nothing_to_do(
    db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch
) -> None:
    project = await _make_project(db_session)
    _add_slide(db_session, project, 1, text="第一页", script="已有讲稿")
    _add_slide(db_session, project, 2, text=None, notes=None)
    await db_session.flush()

    async def fail_if_called(*args: object, **kwargs: object) -> dict[str, Any]:
        raise AssertionError("没有待生成页时不应调用模型")

    monkeypatch.setattr(llm_client, "chat_json", fail_if_called)

    result = await script_ai.generate_for_project(db_session, project, DEFAULTS)

    assert result.status == SCRIPT_AI_STATUS_DONE
    assert result.total == 0
    assert result.skipped == 1


async def test_generate_partial_when_one_batch_fails(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    project = await _make_project(db_session)
    _add_slide(db_session, project, 1, text="第一页文字")
    _add_slide(db_session, project, 2, text="第二页文字")
    await db_session.flush()

    async def flaky_chat_json(messages: list[dict[str, str]], expected_keys: list[str] | None = None) -> dict[str, Any]:
        # batch_size=1：第一次失败、第二次成功
        if "幻灯片 1" in messages[1]["content"]:
            raise LLMProviderError("上游 502")
        return {"slides": [{"slide_no": 2, "script": "第二页稿"}]}

    monkeypatch.setattr(llm_client, "chat_json", flaky_chat_json)

    result = await script_ai.generate_for_project(db_session, project, replace(DEFAULTS, script_ai_batch_size=1))

    assert result.status == SCRIPT_AI_STATUS_PARTIAL
    assert result.done == 1
    assert result.failed == 1

    assert result.errors and "第 1 页生成失败" in result.errors[0]

    refreshed = await db_session.get(PptVideoProject, project.id)
    assert refreshed is not None
    await db_session.refresh(refreshed)
    assert refreshed.script_ai_status == SCRIPT_AI_STATUS_PARTIAL
    assert refreshed.script_ai_error and "第 1 页生成失败" in refreshed.script_ai_error


async def test_generate_failed_when_all_batches_fail(db_session: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    project = await _make_project(db_session)
    _add_slide(db_session, project, 1, text="第一页文字")
    await db_session.flush()

    async def broken_chat_json(
        messages: list[dict[str, str]], expected_keys: list[str] | None = None
    ) -> dict[str, Any]:
        raise LLMProviderError("模型不可用")

    monkeypatch.setattr(llm_client, "chat_json", broken_chat_json)

    result = await script_ai.generate_for_project(db_session, project, DEFAULTS)

    assert result.status == SCRIPT_AI_STATUS_FAILED
    refreshed = await db_session.get(PptVideoProject, project.id)
    assert refreshed is not None
    assert refreshed.script_ai_status == SCRIPT_AI_STATUS_FAILED


async def test_write_if_blank_does_not_overwrite(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    _add_slide(db_session, project, 1, text="第一页文字", script="用户抢先写了")
    await db_session.flush()

    written = await script_ai._write_if_blank(db_session, project.id, 1, "AI 迟到的稿")

    assert written is False
    slide = await db_session.scalar(
        select(PptVideoSlide).where(PptVideoSlide.project_id == project.id, PptVideoSlide.slide_no == 1)
    )
    assert slide is not None
    assert slide.script_text == "用户抢先写了"
    assert slide.script_source == ""


async def test_write_if_blank_fills_whitespace_only_script(db_session: AsyncSession) -> None:
    project = await _make_project(db_session)
    _add_slide(db_session, project, 1, text="第一页文字", script="   \n  ")
    await db_session.flush()

    written = await script_ai._write_if_blank(db_session, project.id, 1, "AI 初稿")

    assert written is True
    slide = await db_session.scalar(
        select(PptVideoSlide).where(PptVideoSlide.project_id == project.id, PptVideoSlide.slide_no == 1)
    )
    assert slide is not None
    assert slide.script_text == "AI 初稿"
    assert slide.script_source == SCRIPT_SOURCE_AI
