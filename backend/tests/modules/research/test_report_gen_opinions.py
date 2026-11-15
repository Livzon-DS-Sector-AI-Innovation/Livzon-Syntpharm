"""意见库：归一化归并、次数累计、生成前汇总与降级。

不连数据库、不调真实 LLM：这里只钉住三件事——
1. 相同写法的意见必须归并成一条并累计次数，否则汇总会被同义句淹没；
2. 意见库为空时不调模型（白花一次调用），有意见时只调一次；
3. 模型不可用必须退回原文清单，不能把生成任务卡住。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest

from app.modules.research.report_gen import opinions as opinions_module
from app.modules.research.report_gen.opinions import (
    build_digest,
    normalize,
    normalized_key,
    record_feedback,
)

NOW = datetime.now(UTC)


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[Any]:
        return list(self._rows)

    def first(self) -> Any:
        return self._rows[0] if self._rows else None


class _Session:
    """够用的假 session：按调用顺序返回预置查询结果。"""

    def __init__(self, results: list[list[Any]] | None = None) -> None:
        self.results = list(results or [])
        self.added: list[Any] = []
        self.flushes = 0
        self.nested = 0

    async def execute(self, _stmt: Any) -> _Result:
        if not self.results:
            raise AssertionError("没有预置更多查询结果")
        return _Result(self.results.pop(0))

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1
        # 真库在 flush 时生成主键；假 session 补上，避免「指针指向 None 却断言相等」
        for obj in self.added:
            if getattr(obj, "id", None) is None:
                obj.id = uuid4()

    def begin_nested(self) -> _Session:
        self.nested += 1
        return self

    async def __aenter__(self) -> _Session:
        return self

    async def __aexit__(self, *_exc: Any) -> bool:
        return False


def _opinion_row(**overrides: Any) -> Any:
    row = SimpleNamespace(
        id=uuid4(),
        content="结果与讨论要写明工艺参数与收率的对应关系",
        normalized_key="key",
        hit_count=3,
        status="active",
        last_feedback_id=None,
        last_seen_at=NOW,
        updated_by=None,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _config(**overrides: Any) -> Any:
    base = {
        "opinion_digest_enabled": True,
        "opinion_max_items": 40,
        "opinion_digest_prompt": "请汇总：\n{items}",
        "model": SimpleNamespace(display="测试模型", call_kwargs=lambda: {}),
    }
    base.update(overrides)
    return SimpleNamespace(**base)


def _job(**overrides: Any) -> Any:
    base = {"id": uuid4(), "opinion_digest_id": None}
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------- 归一化


def test_normalize_collapses_width_space_and_trailing_punctuation() -> None:
    # NFKC 会把全角标点收成半角：归并只求「同义同键」，不追求展示原样
    assert normalize("　结果  与讨论：补因果。 ") == "结果 与讨论:补因果"
    assert normalize(None) == ""


def test_normalized_key_merges_same_opinion_with_different_case() -> None:
    assert normalized_key("Yield should be reported") == normalized_key("yield  should be reported。")
    assert normalized_key("补收率") != normalized_key("补纯度")


# ---------------------------------------------------------------- 入库归并


async def test_record_feedback_creates_new_opinion() -> None:
    session = _Session([[]])
    feedback = SimpleNamespace(id=uuid4(), job_id=uuid4(), content="  补写收率  ", created_at=NOW)

    row = await record_feedback(cast(Any, session), cast(Any, feedback), None)

    assert row is not None
    added = [obj for obj in session.added if getattr(obj, "normalized_key", None)]
    assert len(added) == 1
    assert added[0].content == "补写收率"
    assert added[0].hit_count == 1
    assert added[0].status == "active"
    assert session.nested == 1


def _feedback(content: str) -> Any:
    return SimpleNamespace(id=uuid4(), job_id=uuid4(), content=content, created_at=NOW)


async def test_record_feedback_increments_existing_hit_count() -> None:
    existing: Any = _opinion_row(hit_count=2)
    session = _Session([[existing]])
    feedback = _feedback("结果与讨论要写明工艺参数与收率的对应关系")

    row = await record_feedback(cast(Any, session), cast(Any, feedback), None)

    assert row is not None
    assert row.id == existing.id
    assert existing.hit_count == 3
    assert existing.last_feedback_id == feedback.id
    assert not session.added


async def test_record_feedback_keeps_disabled_opinion_disabled() -> None:
    existing: Any = _opinion_row(status="disabled", hit_count=4)
    session = _Session([[existing]])
    feedback = _feedback("结果与讨论要写明工艺参数与收率的对应关系")

    await record_feedback(cast(Any, session), cast(Any, feedback), None)

    assert existing.status == "disabled"
    assert existing.hit_count == 4


async def test_record_feedback_does_not_raise_when_library_write_fails() -> None:
    """意见库写失败只记日志：原始意见必须留下，不能因为归库失败把提交一起回滚。"""

    class _BrokenSession(_Session):
        async def execute(self, _stmt: Any) -> _Result:
            raise RuntimeError("db down")

    session = _BrokenSession()
    feedback = SimpleNamespace(id=uuid4(), job_id=uuid4(), content="补写收率", created_at=NOW)

    assert await record_feedback(cast(Any, session), cast(Any, feedback), None) is None


# ---------------------------------------------------------------- 生成前汇总


async def test_build_digest_returns_none_when_disabled() -> None:
    session = _Session()
    job = _job()

    assert await build_digest(cast(Any, session), job, _config(opinion_digest_enabled=False)) is None
    assert job.opinion_digest_id is None
    assert not session.added


async def test_build_digest_skips_model_when_library_is_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    async def _chat(*_args: Any, **_kwargs: Any) -> str:
        nonlocal called
        called = True
        return "x"

    monkeypatch.setattr(opinions_module, "llm_client", SimpleNamespace(chat=_chat))
    session = _Session([[]])

    assert await build_digest(cast(Any, session), _job(), _config()) is None
    assert called is False


async def test_build_digest_merges_opinions_and_links_job(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _chat(*_args: Any, **_kwargs: Any) -> str:
        return "1. 结果与讨论必须写明工艺参数与收率的对应关系"

    monkeypatch.setattr(opinions_module, "llm_client", SimpleNamespace(chat=_chat))
    opinions = [_opinion_row(hit_count=5), _opinion_row(content="表格必须有单位", hit_count=2)]
    session = _Session([opinions, []])
    job = _job()

    result = await build_digest(cast(Any, session), job, _config())

    assert result is not None and result.reused is False
    assert result.digest.status == "ok"
    assert result.digest.item_count == 2
    assert result.digest.model_name == "测试模型"
    assert len(result.digest.opinion_ids or []) == 2
    assert job.opinion_digest_id == result.digest.id
    assert session.added == [result.digest]


async def test_build_digest_falls_back_when_model_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _chat(*_args: Any, **_kwargs: Any) -> str:
        raise RuntimeError("模型超时")

    monkeypatch.setattr(opinions_module, "llm_client", SimpleNamespace(chat=_chat))
    opinions = [_opinion_row(content="表格必须有单位"), _opinion_row(content="结论要落到数据")]
    session = _Session([opinions, []])
    job = _job()

    result = await build_digest(cast(Any, session), job, _config())

    assert result is not None
    assert result.digest.status == "fallback"
    assert result.digest.model_name is None
    assert result.digest.item_count == 2
    assert result.digest.digest_text.startswith("1. 表格必须有单位")
    assert job.opinion_digest_id == result.digest.id


async def test_build_digest_reuses_digest_for_same_opinion_set(monkeypatch: pytest.MonkeyPatch) -> None:
    async def _chat(*_args: Any, **_kwargs: Any) -> str:
        raise AssertionError("相同意见集合不应重复调用模型")

    monkeypatch.setattr(opinions_module, "llm_client", SimpleNamespace(chat=_chat))
    existing: Any = SimpleNamespace(id=uuid4(), digest_text="旧汇总", item_count=1, status="ok", source_hash="h")
    session = _Session([[_opinion_row()], [existing]])
    job = _job()

    result = await build_digest(cast(Any, session), job, _config())

    assert result is not None and result.reused is True
    assert result.digest is existing
    assert job.opinion_digest_id == existing.id
    assert not session.added
