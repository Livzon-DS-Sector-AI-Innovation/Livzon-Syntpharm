"""项目知识库召回的适配层测试（假客户端，不打真实 RAGFlow）。"""

from __future__ import annotations

from typing import Any

from app.modules.research.doc_gen.kb_retrieval import KB_FILE_PREFIX, KnowledgeBaseRetriever
from app.modules.research.knowledge_base.ragflow import RagflowError

CHUNK = {
    "content": "原研企业：Kaken Pharmaceutical Co., Ltd.，商品名米诺地尔。",
    "document_keyword": "米诺地尔项目调研报告.docx",
    "document_id": "doc-1",
}


class FakeClient:
    """假 RAGFlow 客户端：只实现召回层用到的那一个方法。"""

    def __init__(
        self,
        chunks: list[dict[str, Any]] | None = None,
        error: Exception | None = None,
        configured: bool = True,
    ):
        self._chunks = chunks if chunks is not None else [CHUNK]
        self._error = error
        self.configured = configured
        self.calls = 0
        self.last_kwargs: dict[str, Any] = {}

    async def retrieval(self, question: str, dataset_ids: list[str], **kwargs: Any) -> list[dict[str, Any]]:
        self.calls += 1
        self.last_kwargs = kwargs
        if self._error is not None:
            raise self._error
        return [dict(chunk) for chunk in self._chunks]


def _retriever(client: FakeClient, **kwargs: Any) -> KnowledgeBaseRetriever:
    return KnowledgeBaseRetriever(["ds-1"], client=client, **kwargs)  # type: ignore[arg-type]


def test_build_query_dedupes_and_limits() -> None:
    assert KnowledgeBaseRetriever.build_query([" 原研企业 ", "原研企业", "米诺地尔"]) == "原研企业 米诺地尔"
    long_query = KnowledgeBaseRetriever.build_query(["关键词" * 100])
    assert len(long_query) == 240


async def test_disabled_without_dataset_or_config() -> None:
    assert not KnowledgeBaseRetriever([], client=FakeClient()).enabled  # type: ignore[arg-type]
    assert not KnowledgeBaseRetriever(["ds-1"], client=FakeClient(configured=False)).enabled  # type: ignore[arg-type]
    empty = KnowledgeBaseRetriever([], client=FakeClient())  # type: ignore[arg-type]
    assert await empty.retrieve(["原研企业"]) == []


async def test_retrieve_converts_chunks_to_blocks() -> None:
    client = FakeClient()
    retriever = _retriever(client)
    blocks = await retriever.retrieve(["原研企业", "米诺地尔"])

    assert len(blocks) == 1
    block = blocks[0]
    assert block.file_id == f"{KB_FILE_PREFIX}米诺地尔项目调研报告.docx"
    assert block.text.startswith("原研企业：Kaken")
    assert retriever.stats.hits == 1
    assert retriever.stats.sources == {block.file_id: "米诺地尔项目调研报告.docx"}
    assert client.last_kwargs["top_k"] == 6


async def test_retrieve_dedupes_identical_content() -> None:
    client = FakeClient(chunks=[CHUNK, dict(CHUNK)])
    blocks = await _retriever(client).retrieve(["原研企业"])
    assert len(blocks) == 1


async def test_retrieve_skips_too_short_content() -> None:
    client = FakeClient(chunks=[{"content": "  ", "document_keyword": "x.docx"}])
    assert await _retriever(client).retrieve(["原研企业"]) == []


async def test_retrieve_uses_cache_for_same_query() -> None:
    """同一批次的多个槽位常共用检索词，相同查询串只打一次知识库。"""
    client = FakeClient()
    retriever = _retriever(client)
    await retriever.retrieve(["原研企业", "米诺地尔"])
    await retriever.retrieve(["原研企业", "米诺地尔"])

    assert client.calls == 1
    assert retriever.stats.cached == 1


async def test_failure_degrades_to_empty() -> None:
    client = FakeClient(error=RagflowError("知识库服务连接失败"))
    retriever = _retriever(client)

    assert await retriever.retrieve(["原研企业"]) == []
    assert retriever.stats.failures == 1
    # 失败也要记缓存：同一批次的相同检索词不重复打失败请求
    assert await retriever.retrieve(["原研企业"]) == []
    assert client.calls == 1


async def test_timeout_degrades_to_empty() -> None:
    """召回超时按降级处理（提取退回仅用本地资料）。"""
    client = FakeClient(error=TimeoutError())
    assert await _retriever(client).retrieve(["原研企业"]) == []
