"""研发文档生成 — 候选块检索。

双路召回：关键词倒排索引 + 向量余弦相似度，融合排序后返回候选块。
- 关键词路径：中文无空格按子串命中；纯英文数字关键词按词边界命中；
- 向量路径：embedding 余弦相似度，捕获语义相关但关键词不匹配的块；
- 融合策略：两路分数归一化后加权求和（关键词权重 alpha，向量权重 1-alpha）；
- 命中块前后 expand_neighbors 个同文件相邻块作为上下文一起纳入候选。
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any

from app.modules.research.doc_gen.parsing import TextBlock

logger = logging.getLogger(__name__)

# 视为"英文词"的关键词：纯 ASCII 字母数字（含常见单位/编号符号），需按词边界匹配
_ASCII_WORD_RE = re.compile(r"^[a-z0-9][a-z0-9_.\-]*$")
# 打分权重常量
_DISTINCT_WEIGHT = 2.0  # 每命中一个不同关键词的基础分
_REPEAT_WEIGHT = 0.2  # 同一关键词超出首次命中的每次重复的加分
_REPEAT_CAP = 10  # 重复命中加分的次数上限，防止刷词
_LEN_NORM_BASE = 500.0  # 长度归一化基数：score = raw / (1 + len/基数)
_NEIGHBOR_DECAY = 0.2  # 邻居块继承命中块的分数的衰减系数（按距离倒数）


def _count_hits(lowered_text: str, keyword: str, pattern_cache: dict[str, re.Pattern[str]]) -> int:
    """统计单个关键词在（已小写）文本中的命中次数。"""
    if not keyword:
        return 0
    if _ASCII_WORD_RE.match(keyword):
        pattern = pattern_cache.get(keyword)
        if pattern is None:
            pattern = re.compile(rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])")
            pattern_cache[keyword] = pattern
        return len(pattern.findall(lowered_text))
    # 含非 ASCII（如中文）或带空格的关键词：直接子串计数
    return lowered_text.count(keyword)


def score_text(text: str, keywords: Sequence[str], pattern_cache: dict[str, re.Pattern[str]]) -> float:
    """对单个块文本按关键词打分；无任何关键词命中时返回 0。

    公开给提取层复用：候选块进入 prompt 前按本槽位（或本批槽位）关键词重新计分，
    作为上下文预算内贪心挑选的依据。
    """
    lowered = text.lower()
    distinct = 0
    total = 0
    for kw in keywords:
        c = _count_hits(lowered, kw, pattern_cache)
        if c > 0:
            distinct += 1
            total += c
    if distinct == 0:
        return 0.0
    raw = _DISTINCT_WEIGHT * distinct + _REPEAT_WEIGHT * min(total - distinct, _REPEAT_CAP)
    return raw / (1.0 + len(text) / _LEN_NORM_BASE)


class BlockRetriever:
    """基于解析产物 TextBlock 列表的检索器，支持关键词 + 向量双路召回。

    构造时预建倒排索引（关键词 → 候选块位置列表），后续检索直接查索引而非全量遍历。
    可选注入 ``vector_index``（VectorIndex 实例）启用向量融合检索：
    - 关键词路径：倒排索引 + 打分
    - 向量路径：embedding 余弦相似度
    - 融合：两路分数归一化后加权求和
    """

    def __init__(
        self,
        blocks: Sequence[TextBlock],
        *,
        vector_index: Any = None,
        vector_alpha: float = 0.6,
    ) -> None:
        self._blocks: list[TextBlock] = list(blocks)
        # file_id -> {块内 index: 在 _blocks 中的位置}，用于邻居扩展
        self._by_file: dict[str, dict[int, int]] = defaultdict(dict)
        for pos, block in enumerate(self._blocks):
            self._by_file[block.file_id][block.index] = pos
        # 倒排索引：归一化关键词 → 命中的块位置列表（构造时一次性建好）
        self._inverted: dict[str, list[int]] = defaultdict(list)
        self._build_inverted_index()
        # 向量索引（可选）
        self._vector_index = vector_index
        # 融合权重：alpha 控制关键词路径权重，1-alpha 为向量路径权重
        self._vector_alpha = max(0.0, min(1.0, vector_alpha))

    def _build_inverted_index(self) -> None:
        """预建倒排索引：对每个块提取所有可能的检索关键词并记录位置。

        索引粒度：中文按 2-4 字片段 + 整块可检索子串；英文按词边界。
        只索引长度 ≥ 2 的关键词，避免单字噪音。
        """
        for pos, block in enumerate(self._blocks):
            text = block.text
            if not text:
                continue
            lowered = text.lower()
            # 英文词：按非字母数字分割
            for word in re.findall(r"[a-z0-9][a-z0-9_.\-]*", lowered):
                if len(word) >= 2:
                    self._inverted[word].append(pos)
            # 中文：提取 2-4 字片段（覆盖大部分专业术语长度）
            cjk_runs = re.findall(r"[\u4e00-\u9fff]{2,}", lowered)
            for run in cjk_runs:
                for gram_len in (2, 3, 4):
                    for start in range(len(run) - gram_len + 1):
                        gram = run[start : start + gram_len]
                        self._inverted[gram].append(pos)
        # 去重：同一块对同一关键词只记一次
        for key in self._inverted:
            self._inverted[key] = sorted(set(self._inverted[key]))

    @staticmethod
    def _resolve_allowed_files(
        roles: Mapping[str, Sequence[str]] | None,
        allow_file_ids: Sequence[str] | None,
    ) -> set[str] | None:
        """合并两类文件过滤：allow_file_ids 白名单 ∩ roles 中允许角色非空的文件。None 表示不过滤。"""
        allowed: set[str] | None = None
        if allow_file_ids is not None:
            allowed = set(allow_file_ids)
        if roles is not None:
            role_files = {file_id for file_id, rs in roles.items() if rs}
            allowed = role_files if allowed is None else allowed & role_files
        return allowed

    def candidates(
        self,
        keywords: Sequence[str],
        *,
        limit: int = 8,
        roles: Mapping[str, Sequence[str]] | None = None,
        allow_file_ids: Sequence[str] | None = None,
        expand_neighbors: int = 1,
    ) -> list[TextBlock]:
        """返回按 (page, index) 升序排列的候选块，便于直接交给模型阅读上下文。

        - 命中块按分数降序竞争 limit 名额；邻居块带衰减分一起参与排序；
        - 空输入、全空关键词、limit<=0 均安全返回 []。
        - 使用倒排索引预筛候选位置，避免全量遍历所有块。
        """
        cleaned = [kw.strip().lower() for kw in keywords if kw and kw.strip()]
        if not cleaned or not self._blocks or limit <= 0:
            return []

        allowed = self._resolve_allowed_files(roles, allow_file_ids)
        pattern_cache: dict[str, re.Pattern[str]] = {}

        # 倒排索引预筛：只遍历可能命中的块位置
        candidate_positions: set[int] = set()
        for kw in cleaned:
            positions = self._inverted.get(kw)
            if positions:
                candidate_positions.update(positions)
        # 倒排索引未覆盖的关键词（如长中文术语 > 4 字），回退全量扫描
        uncovered_keywords = [kw for kw in cleaned if kw not in self._inverted]
        if uncovered_keywords:
            for pos, block in enumerate(self._blocks):
                if allowed is not None and block.file_id not in allowed:
                    continue
                candidate_positions.add(pos)

        hits: list[tuple[float, int]] = []  # (score, 位置)
        for pos in candidate_positions:
            block = self._blocks[pos]
            if allowed is not None and block.file_id not in allowed:
                continue
            score = score_text(block.text, cleaned, pattern_cache)
            if score > 0:
                hits.append((score, pos))
        if not hits:
            return []

        # 命中块 + 同文件前后邻居（按 index），去重取最大分
        selected: dict[int, float] = {pos: score for score, pos in hits}
        if expand_neighbors > 0:
            for score, pos in hits:
                block = self._blocks[pos]
                index_map = self._by_file[block.file_id]
                for offset in range(-expand_neighbors, expand_neighbors + 1):
                    if offset == 0:
                        continue
                    neighbor_pos = index_map.get(block.index + offset)
                    if neighbor_pos is None:
                        continue
                    # 邻居继承衰减分，保证在 limit 截断时优先于零分噪音被保留
                    neighbor_score = score * _NEIGHBOR_DECAY / max(abs(offset), 1)
                    if neighbor_score > selected.get(neighbor_pos, 0.0):
                        selected[neighbor_pos] = neighbor_score

        ordered = sorted(
            selected.items(),
            key=lambda item: (-item[1], self._blocks[item[0]].page, self._blocks[item[0]].index, item[0]),
        )
        picked = [self._blocks[pos] for pos, _ in ordered[:limit]]
        # 返回时恢复阅读顺序：按 (page, index) 升序；跨文件时再按 file_id 稳定排序
        picked.sort(key=lambda b: (b.page, b.index, b.file_id))
        return picked

    async def candidates_with_vector(
        self,
        keywords: Sequence[str],
        *,
        query_text: str = "",
        embed_fn: Any = None,
        limit: int = 8,
        roles: Mapping[str, Sequence[str]] | None = None,
        allow_file_ids: Sequence[str] | None = None,
        expand_neighbors: int = 1,
    ) -> list[TextBlock]:
        """双路召回：关键词 + 向量融合检索。

        当 ``vector_index`` 已构建且 ``embed_fn`` 可用时，执行双路召回：
        1. 关键词路径：倒排索引 + 打分（同 ``candidates()``）
        2. 向量路径：query_text embedding → 余弦相似度
        3. 融合：两路分数归一化后加权求和（alpha 控制关键词权重）

        当向量索引不可用时，退化为纯关键词检索（等同 ``candidates()``）。

        Args:
            keywords: 关键词列表（用于关键词路径）
            query_text: 查询文本（用于向量路径，通常是槽位的 search_terms 拼接）
            embed_fn: embedding 函数，签名 ``async (texts: list[str]) -> list[list[float]]``
            limit: 返回块数上限
            roles: 文件角色过滤
            allow_file_ids: 文件白名单
            expand_neighbors: 邻居扩展数
        """
        # 向量索引不可用，退化为纯关键词检索
        if self._vector_index is None or not self._vector_index.is_built or embed_fn is None:
            return self.candidates(
                keywords,
                limit=limit,
                roles=roles,
                allow_file_ids=allow_file_ids,
                expand_neighbors=expand_neighbors,
            )

        cleaned = [kw.strip().lower() for kw in keywords if kw and kw.strip()]
        if not cleaned or not self._blocks or limit <= 0:
            return []

        allowed = self._resolve_allowed_files(roles, allow_file_ids)
        allowed_indices = self._get_allowed_indices(allowed) if allowed is not None else None

        # === 关键词路径 ===
        kw_scores: dict[int, float] = {}
        pattern_cache: dict[str, re.Pattern[str]] = {}
        candidate_positions: set[int] = set()
        for kw in cleaned:
            positions = self._inverted.get(kw)
            if positions:
                candidate_positions.update(positions)
        uncovered_keywords = [kw for kw in cleaned if kw not in self._inverted]
        if uncovered_keywords:
            for pos, block in enumerate(self._blocks):
                if allowed is not None and block.file_id not in allowed:
                    continue
                candidate_positions.add(pos)
        for pos in candidate_positions:
            block = self._blocks[pos]
            if allowed is not None and block.file_id not in allowed:
                continue
            score = score_text(block.text, cleaned, pattern_cache)
            if score > 0:
                kw_scores[pos] = score

        # === 向量路径 ===
        vec_scores: dict[int, float] = {}
        if query_text.strip():
            try:
                query_vector = (await embed_fn([query_text]))[0]
                vec_results = self._vector_index.search(
                    query_vector,
                    top_k=limit * 2,  # 多取一些，融合后再截断
                    allowed_indices=allowed_indices,
                    min_score=0.3,
                )
                vec_scores = {pos: score for pos, score in vec_results}
            except Exception:
                logger.exception("向量检索失败，退化为纯关键词检索")

        # === 融合 ===
        fused = self._fuse_scoreses(kw_scores, vec_scores)
        if not fused:
            return []

        # 邻居扩展
        selected: dict[int, float] = dict(fused)
        if expand_neighbors > 0:
            # 只对关键词命中的块做邻居扩展（向量命中的块已经包含语义上下文）
            for pos, score in kw_scores.items():
                block = self._blocks[pos]
                index_map = self._by_file[block.file_id]
                for offset in range(-expand_neighbors, expand_neighbors + 1):
                    if offset == 0:
                        continue
                    neighbor_pos = index_map.get(block.index + offset)
                    if neighbor_pos is None:
                        continue
                    neighbor_score = score * _NEIGHBOR_DECAY / max(abs(offset), 1)
                    if neighbor_score > selected.get(neighbor_pos, 0.0):
                        selected[neighbor_pos] = neighbor_score

        ordered = sorted(
            selected.items(),
            key=lambda item: (-item[1], self._blocks[item[0]].page, self._blocks[item[0]].index, item[0]),
        )
        picked = [self._blocks[pos] for pos, _ in ordered[:limit]]
        picked.sort(key=lambda b: (b.page, b.index, b.file_id))
        return picked

    def _get_allowed_indices(self, allowed_files: set[str]) -> set[int]:
        """将文件白名单转换为块索引集合，供向量检索使用。"""
        indices: set[int] = set()
        for pos, block in enumerate(self._blocks):
            if block.file_id in allowed_files:
                indices.add(pos)
        return indices

    def _fuse_scoreses(
        self,
        kw_scores: dict[int, float],
        vec_scores: dict[int, float],
    ) -> dict[int, float]:
        """融合两路分数：归一化后加权求和。

        归一化方式：min-max 归一化到 [0, 1]，然后按 alpha 加权。
        当某一路为空时，另一路权重自动提升到 1.0。
        """
        all_positions = set(kw_scores.keys()) | set(vec_scores.keys())
        if not all_positions:
            return {}

        # 单路退化
        if not vec_scores:
            return kw_scores
        if not kw_scores:
            # 纯向量结果，按 alpha=0 处理
            return {pos: score for pos, score in vec_scores.items()}

        # 归一化关键词分数
        kw_values = list(kw_scores.values())
        kw_min, kw_max = min(kw_values), max(kw_values)
        kw_range = kw_max - kw_min if kw_max > kw_min else 1.0

        # 归一化向量分数
        vec_values = list(vec_scores.values())
        vec_min, vec_max = min(vec_values), max(vec_values)
        vec_range = vec_max - vec_min if vec_max > vec_min else 1.0

        alpha = self._vector_alpha
        fused: dict[int, float] = {}
        for pos in all_positions:
            kw_norm = (kw_scores.get(pos, 0.0) - kw_min) / kw_range if pos in kw_scores else 0.0
            vec_norm = (vec_scores.get(pos, 0.0) - vec_min) / vec_range if pos in vec_scores else 0.0
            fused[pos] = alpha * kw_norm + (1.0 - alpha) * vec_norm
        return fused
