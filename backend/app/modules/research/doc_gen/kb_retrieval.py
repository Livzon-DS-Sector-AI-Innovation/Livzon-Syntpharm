"""项目知识库召回适配：把 RAGFlow 命中的切片包装成提取链路认识的 TextBlock。

为什么按槽位现取、而不是启动时把整个知识库灌进 ctx.blocks：

- 全库切片动辄数千条，注入后会撑爆 prompt 预算，也会拖慢本地关键词检索；
- 每个槽位的检索意图不同，RAGFlow 自身的混合检索（关键词 + 向量）比本地二次筛选更准。

因此提取时逐槽位调一次召回，命中片段以 ``file_id = "kb:{文档名}"`` 作为「虚拟资料」
参与 prompt 与证据回检——回检语料按同一 file_id 注册，所以引用核对逻辑与普通资料完全一致。

失败语义：知识库不可用时只记 warning 并返回空列表，提取退回「仅用本地资料」，
绝不让任务因为外部服务抖动而失败。
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Sequence
from dataclasses import dataclass, field

from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.knowledge_base.ragflow import RagflowClient, RagflowError

logger = logging.getLogger(__name__)

# 知识库虚拟文件前缀（角色常量 KNOWLEDGE_ROLE 集中定义在 extraction.py）
KB_FILE_PREFIX = "kb:"
# 命中片段在 prompt 中的排序加权：知识库是语义召回结果，应优先进入上下文，
# 但不能挤掉本地资料的强关键词命中，故取「两次关键词命中」量级的加性权重
KB_POOL_PRIORITY = 2.0

# 同一查询串的召回结果在任务内复用（同一批次的多个槽位常共用检索词）
_QUERY_CACHE_LIMIT = 256
# 并发上限：提取批次并行时不把知识库服务打满
_MAX_CONCURRENT_CALLS = 4
# 传给知识库服务的查询串长度上限
_MAX_QUERY_CHARS = 240


@dataclass(slots=True)
class KbRetrievalStats:
    """知识库召回统计（并入任务 stats，供生成说明与排查）。"""

    calls: int = 0
    hits: int = 0
    failures: int = 0
    cached: int = 0
    # file_id → 文档名，供产物说明标注「这一稿参考了哪些知识库文档」
    sources: dict[str, str] = field(default_factory=dict)


class KnowledgeBaseRetriever:
    """按槽位检索词从项目知识库召回切片。"""

    def __init__(
        self,
        dataset_ids: Sequence[str],
        *,
        top_k: int = 6,
        similarity_threshold: float = 0.2,
        vector_similarity_weight: float = 0.3,
        timeout_seconds: int = 30,
        client: RagflowClient | None = None,
    ) -> None:
        self._dataset_ids = [str(d) for d in dataset_ids if d]
        self._top_k = max(1, top_k)
        self._similarity_threshold = similarity_threshold
        self._vector_similarity_weight = vector_similarity_weight
        self._timeout_seconds = max(1, timeout_seconds)
        self._client = client or RagflowClient()
        self._cache: dict[str, list[TextBlock]] = {}
        self._semaphore = asyncio.Semaphore(_MAX_CONCURRENT_CALLS)
        self.stats = KbRetrievalStats()

    @property
    def enabled(self) -> bool:
        """数据集与凭证都就绪才启用。"""
        return bool(self._dataset_ids) and self._client.configured

    @staticmethod
    def build_query(keywords: Sequence[str]) -> str:
        """把槽位检索词拼成召回问句（去重、限长）。"""
        seen: list[str] = []
        for keyword in keywords:
            token = (keyword or "").strip()
            if token and token not in seen:
                seen.append(token)
        return " ".join(seen)[:_MAX_QUERY_CHARS]

    async def retrieve(self, keywords: Sequence[str]) -> list[TextBlock]:
        """召回并转换为 TextBlock；任何失败都降级为空列表。"""
        if not self.enabled:
            return []
        query = self.build_query(keywords)
        if not query:
            return []
        cached = self._cache.get(query)
        if cached is not None:
            self.stats.cached += 1
            return list(cached)

        self.stats.calls += 1
        async with self._semaphore:
            try:
                chunks = await asyncio.wait_for(
                    self._client.retrieval(
                        query,
                        self._dataset_ids,
                        top_k=self._top_k,
                        similarity_threshold=self._similarity_threshold,
                        vector_similarity_weight=self._vector_similarity_weight,
                    ),
                    timeout=self._timeout_seconds,
                )
            except (RagflowError, TimeoutError) as exc:
                self.stats.failures += 1
                reason = exc.message if isinstance(exc, RagflowError) else f"召回超时（>{self._timeout_seconds}s）"
                logger.warning(
                    "知识库召回失败，本次仅用本地资料",
                    extra={"query": query[:60], "error": reason, "module_name": "research"},
                )
                self._remember(query, [])
                return []

        blocks = self._to_blocks(chunks)
        self.stats.hits += len(blocks)
        self._remember(query, blocks)
        return blocks

    def _remember(self, query: str, blocks: list[TextBlock]) -> None:
        if len(self._cache) >= _QUERY_CACHE_LIMIT:
            self._cache.clear()
        self._cache[query] = list(blocks)

    def _to_blocks(self, chunks: Sequence[dict[str, object]]) -> list[TextBlock]:
        """切片 → TextBlock：同一文档内按召回顺序编号，重复内容只保留一次。"""
        blocks: list[TextBlock] = []
        seen: set[tuple[str, str]] = set()
        counters: dict[str, int] = {}
        for chunk in chunks:
            content = str(chunk.get("content") or "").strip()
            if len(content) < 4:
                continue
            document_name = str(chunk.get("document_keyword") or chunk.get("document_id") or "知识库文档")
            file_id = f"{KB_FILE_PREFIX}{document_name}"
            key = (file_id, content[:80])
            if key in seen:
                continue
            seen.add(key)
            index = counters.get(file_id, 0)
            counters[file_id] = index + 1
            blocks.append(TextBlock(file_id=file_id, page=1, index=index, text=content, kind="paragraph"))
            self.stats.sources[file_id] = document_name
        return blocks
