"""facts.py 增量镜像的 prune 门控回归测试。

Bug 场景：截断（max_chunks）、取消（should_cancel）或读取失败（RagflowError）后
``remote_ids`` 不完整——没列到的切片只是「还没翻到」，不代表远端删了；
照常 prune 会把已镜像到本地的切片连同其事实误删。因此清理只允许在
该文档远端切片**完整枚举**后进行。
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any

import pytest

from app.modules.research.knowledge_base import facts
from app.modules.research.knowledge_base.ragflow import RagflowError


class _FakeClient:
    """分页假客户端：pages[i] 是第 i+1 页；fail_from 指定从第几页起抛错。"""

    def __init__(self, pages: list[list[dict[str, Any]]], *, fail_from: int | None = None) -> None:
        self.pages = pages
        self.fail_from = fail_from

    async def list_document_chunks(
        self, dataset_id: str, document_id: str, *, page: int, page_size: int
    ) -> tuple[int, list[dict[str, Any]]]:
        if self.fail_from is not None and page >= self.fail_from:
            raise RagflowError("connection reset")
        index = page - 1
        chunks = self.pages[index] if 0 <= index < len(self.pages) else []
        total = sum(len(p) for p in self.pages)
        return total, chunks


class _FakeSession:
    """只满足 index_chunks 用到的接口：文档查询返回固定行，flush 为空操作。"""

    def __init__(self, documents: list[Any]) -> None:
        self._documents = documents

    async def execute(self, _statement: Any) -> Any:
        documents = self._documents

        class _Result:
            def scalars(self) -> Any:
                return self

            def all(self) -> list[Any]:
                return list(documents)

        return _Result()

    async def flush(self) -> None:
        return None


def _fake_session(documents: list[Any]) -> Any:
    """工厂包装：给 mypy 返回 Any，替身不必伪装成 AsyncSession。"""
    return _FakeSession(documents)


@pytest.fixture
def mirror(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[Any]]:
    """把 _upsert/_prune 换成记录器：upsert 收集 id 并计数，prune 记录调用与快照。"""
    calls: dict[str, list[Any]] = {"upsert": [], "prune": []}

    async def _fake_upsert(
        session: Any, kb: Any, document: Any, chunks: list[dict[str, Any]], remote_ids: set[str], stats: Any
    ) -> None:
        calls["upsert"].append([str(chunk["id"]) for chunk in chunks])
        for chunk in chunks:
            remote_ids.add(str(chunk["id"]))
            stats.chunks_seen += 1

    async def _fake_prune(session: Any, kb: Any, document: Any, remote_ids: set[str], stats: Any) -> None:
        calls["prune"].append(set(remote_ids))

    monkeypatch.setattr(facts, "_upsert_document_chunks", _fake_upsert)
    monkeypatch.setattr(facts, "_prune_missing_chunks", _fake_prune)
    return calls


def _kb() -> Any:
    return SimpleNamespace(id=uuid.uuid4(), status="active", ragflow_dataset_id="ds-1")


def _doc(name: str) -> Any:
    return SimpleNamespace(
        id=uuid.uuid4(),
        file_name=name,
        run_status="DONE",
        ragflow_document_id=f"doc-{name}",
        created_at=datetime.now(UTC),
    )


def _chunk(cid: str) -> dict[str, Any]:
    return {"id": cid, "content": f"text-{cid}"}


async def test_prune_runs_after_complete_listing(mirror: dict[str, list[Any]]) -> None:
    """一页拉完（page*page_size >= total）：允许清理，且携带全部远端 id。"""
    client = _FakeClient([[_chunk("c1"), _chunk("c2")]])
    stats = await facts.index_chunks(_fake_session([_doc("a.pdf")]), _kb(), client=client, page_size=100, max_chunks=0)
    assert stats.truncated is False
    assert mirror["prune"] == [{"c1", "c2"}]


async def test_prune_runs_with_empty_set_when_remote_cleared(mirror: dict[str, list[Any]]) -> None:
    """远端一页返回空 = 切片确实全被删了：允许清理（空集合 → 本地全软删）。"""
    client = _FakeClient([[]])
    await facts.index_chunks(_fake_session([_doc("a.pdf")]), _kb(), client=client, page_size=100, max_chunks=0)
    assert mirror["prune"] == [set()]


async def test_prune_skipped_when_truncated(mirror: dict[str, list[Any]]) -> None:
    """max_chunks 截断：还有下一页没翻，禁止清理，否则未镜像页的本地切片被误删。"""
    client = _FakeClient([[_chunk("c1")], [_chunk("c2")]])
    stats = await facts.index_chunks(_fake_session([_doc("a.pdf")]), _kb(), client=client, page_size=1, max_chunks=1)
    assert stats.truncated is True
    assert mirror["upsert"] == [["c1"]]
    assert mirror["prune"] == []


async def test_prune_skipped_when_cancelled(mirror: dict[str, list[Any]]) -> None:
    """翻页途中取消：remote_ids 只覆盖第一页，禁止清理。"""
    client = _FakeClient([[_chunk("c1")], [_chunk("c2")]])
    probes = iter([False, False, True])  # 文档循环检查、第 1 页检查、第 2 页检查
    stats = await facts.index_chunks(
        _fake_session([_doc("a.pdf")]),
        _kb(),
        client=client,
        page_size=1,
        max_chunks=0,
        should_cancel=lambda: next(probes),
    )
    assert stats.chunks_seen == 1
    assert mirror["prune"] == []


async def test_prune_skipped_when_read_error(mirror: dict[str, list[Any]]) -> None:
    """第二页读取失败：第一页之外的远端切片状态未知，禁止清理并记警告。"""
    client = _FakeClient([[_chunk("c1")], [_chunk("c2")]], fail_from=2)
    stats = await facts.index_chunks(_fake_session([_doc("a.pdf")]), _kb(), client=client, page_size=1, max_chunks=0)
    assert len(stats.warnings) == 1
    assert mirror["prune"] == []


async def test_truncated_stops_remaining_documents(mirror: dict[str, list[Any]]) -> None:
    """截断后外层直接停止：后续文档不处理，也不得被清理。"""
    docs = [_doc("a.pdf"), _doc("b.pdf")]
    client = _FakeClient([[_chunk("c1")], [_chunk("c2")]])
    stats = await facts.index_chunks(_fake_session(docs), _kb(), client=client, page_size=1, max_chunks=1)
    assert stats.documents == 1
    assert mirror["prune"] == []
