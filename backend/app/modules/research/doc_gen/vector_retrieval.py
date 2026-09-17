"""内存向量检索：embedding + 余弦相似度，与关键词检索融合做双路召回。

设计原则：
- 不依赖 pgvector / FAISS 等外部服务，纯 numpy 实现
- 向量矩阵在任务生命周期内驻留内存，任务结束释放
- embedding 调用走 LLMClient.embed()，复用现有配置体系
- 批量 embedding 减少 API 调用次数
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

from .parsing import TextBlock

logger = logging.getLogger(__name__)


class VectorIndex:
    """内存向量索引：存储 TextBlock 的 embedding 向量，支持批量余弦相似度查询。

    构造时不立即计算 embedding，调用 ``build()`` 时才批量调 embedding API。
    这样可以在解析阶段先创建空索引，等所有块就绪后一次性构建。
    """

    def __init__(self, blocks: list[TextBlock], *, embed_fn: Any = None) -> None:
        self._blocks = blocks
        self._embed_fn = embed_fn
        # 向量矩阵：(n_blocks, dim)，构建后填充
        self._matrix: np.ndarray | None = None
        self._dim: int = 0
        self._built: bool = False
        self._failed_indices: set[int] = set()

    @property
    def is_built(self) -> bool:
        return self._built

    @property
    def block_count(self) -> int:
        return len(self._blocks)

    async def build(self, *, batch_size: int = 32) -> None:
        """批量调用 embedding API 构建向量矩阵。

        Args:
            batch_size: 每批 embedding 的文本数，避免单次请求过大
        """
        if self._embed_fn is None:
            logger.warning("向量索引未配置 embedding 函数，跳过构建")
            return
        if not self._blocks:
            self._built = True
            return

        texts = [block.text for block in self._blocks]
        all_vectors: list[list[float]] = []

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            try:
                vectors = await self._embed_fn(batch)
                all_vectors.extend(vectors)
            except Exception:
                logger.exception("embedding 批量调用失败", extra={"batch_start": start, "batch_size": len(batch)})
                # 失败的批次用零向量占位，后续查询时这些块不会被命中
                dim = self._dim or (len(all_vectors[0]) if all_vectors else 1536)
                self._dim = dim
                for i in range(len(batch)):
                    self._failed_indices.add(start + i)
                    all_vectors.append([0.0] * dim)

        if all_vectors:
            self._dim = len(all_vectors[0])
            self._matrix = np.array(all_vectors, dtype=np.float32)
            # L2 归一化：后续余弦相似度 = 矩阵点积
            norms = np.linalg.norm(self._matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            self._matrix = self._matrix / norms

        self._built = True
        logger.info(
            "向量索引构建完成",
            extra={"blocks": len(self._blocks), "dim": self._dim, "failed": len(self._failed_indices)},
        )

    def search(
        self,
        query_vector: list[float],
        *,
        top_k: int = 10,
        allowed_indices: set[int] | None = None,
        min_score: float = 0.3,
    ) -> list[tuple[int, float]]:
        """余弦相似度检索，返回 (block_index, score) 列表。

        Args:
            query_vector: 查询文本的 embedding 向量
            top_k: 返回前 K 个最相似的块
            allowed_indices: 只在这些块索引中搜索（用于文件白名单过滤）
            min_score: 最低相似度阈值，低于此值的块不返回

        Returns:
            按相似度降序排列的 (block_index, score) 列表
        """
        if self._matrix is None or not self._built:
            return []

        q = np.array(query_vector, dtype=np.float32)
        q_norm = np.linalg.norm(q)
        if q_norm == 0:
            return []
        q = q / q_norm

        # 全量点积 = 余弦相似度（已归一化）
        scores = self._matrix @ q

        # 过滤失败块
        if self._failed_indices:
            for idx in self._failed_indices:
                if idx < len(scores):
                    scores[idx] = -1.0

        # 文件白名单过滤
        if allowed_indices is not None:
            mask = np.full(len(scores), -1.0)
            for idx in allowed_indices:
                if idx < len(scores):
                    mask[idx] = scores[idx]
            scores = mask

        # 取 top_k
        if len(scores) <= top_k:
            indices = np.argsort(scores)[::-1]
        else:
            # 使用 argpartition 做部分排序，更快
            partitioned = np.argpartition(scores, -top_k)[-top_k:]
            indices = partitioned[np.argsort(scores[partitioned])[::-1]]

        results = []
        for idx in indices:
            score = float(scores[idx])
            if score >= min_score:
                results.append((int(idx), score))
        return results


async def embed_texts(texts: list[str], *, llm_client: Any, model_name: str | None = None) -> list[list[float]]:
    """调用 LLMClient.embed() 的便捷包装，处理空输入和异常。"""
    if not texts:
        return []
    try:
        return await llm_client.embed(texts, model_override=model_name)
    except Exception:
        logger.exception("embedding 调用失败", extra={"text_count": len(texts)})
        return []
