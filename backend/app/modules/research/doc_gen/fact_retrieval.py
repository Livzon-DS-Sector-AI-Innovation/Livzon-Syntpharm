"""知识库事实召回适配：把结构化事实包装成提取链路认识的 TextBlock。

与 ``kb_retrieval`` 的关系：两者产出的都是 ``file_id = "kb:{文档名}"`` 的虚拟资料，
对提取链路完全同构（同样的角色白名单、同样的证据回检语料登记），可互相替代与兜底。
区别在数据来源——

- ``kb_retrieval``：按槽位实时问 RAGFlow（按需、跨进程、覆盖受查询词限制）；
- ``fact_retrieval``：直接对本地事实库按检索词匹配（零外部调用、快、覆盖全库已抽事实）。

事实的 ``quote`` 在入库时已做过一次证据回检（必须能在源切片中定位），因此这里以
``quote`` 作为 TextBlock 正文：模型引用它时，回检语料里天然存在，不会被误判成「无依据」。
事实库为空时返回空列表，提取自动退回 RAGFlow 实时召回——两者互补，互不阻塞。
"""

from __future__ import annotations

import logging
import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from app.modules.research.doc_gen.kb_retrieval import KB_FILE_PREFIX
from app.modules.research.doc_gen.parsing import TextBlock

logger = logging.getLogger(__name__)

# 进入 prompt 的单条事实文本上限（quote 已在入库时截断，这里只兜底异常长值）
MAX_FACT_TEXT_CHARS = 1200
# 归一化后短于该长度的检索词不参与匹配（「的」「和」等噪声词无区分度）
_MIN_KEYWORD_CHARS = 2
# 命中事实在 prompt 里的排序权重：核心域（主体/谓词/值）命中比仅在引用中命中更重要
_CORE_WEIGHT = 2.0
_QUOTE_WEIGHT = 1.0
# 人工锁定事实的加成：一旦人工确认过，应在与自动事实同分时优先进入上下文
_LOCKED_BONUS = 0.5


def _normalize(text: str) -> str:
    """与提取链路的证据回检保持同一套归一化：NFKC + 小写 + 去全部空白。"""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text or "")).lower()


@dataclass(slots=True)
class FactRetrievalStats:
    """事实召回统计（并入任务 stats，供生成说明与排查）。"""

    queries: int = 0
    hits: int = 0
    matched_facts: int = 0
    # file_id → 文档名，供产物说明标注「这一稿参考了哪些知识库文档」
    sources: dict[str, str] = field(default_factory=dict)


class FactRetriever:
    """按槽位检索词从本地事实库匹配事实并转成虚拟资料块。

    构造时对全库事实做一次归一化预处理，之后的每次召回都是纯内存匹配——
    这是相对 RAGFlow 实时检索的主要收益：同一槽位批量提问时不再逐个打远端接口。
    """

    def __init__(
        self,
        facts: Sequence[Any],
        *,
        top_k: int = 8,
        max_text_chars: int = MAX_FACT_TEXT_CHARS,
    ) -> None:
        self._facts = list(facts)
        self._top_k = max(1, top_k)
        self._max_text_chars = max(64, max_text_chars)
        self.stats = FactRetrievalStats()
        # 预归一化检索域：避免每次查询都重复归一化全库事实
        self._prepared: list[tuple[Any, str, str]] = []
        for fact in self._facts:
            subject = _normalize(getattr(fact, "subject", "") or "")
            predicate = _normalize(getattr(fact, "predicate", "") or "")
            value = _normalize(getattr(fact, "value", "") or "")
            unit = _normalize(getattr(fact, "unit", "") or "")
            quote = _normalize(getattr(fact, "quote", "") or "")
            # 核心域 = 主体+谓词+值+单位：命中它说明事实的属性与槽位诉求一致
            self._prepared.append((fact, f"{subject}{predicate}{value}{unit}", quote))

    @property
    def enabled(self) -> bool:
        """事实库有内容才启用。"""
        return bool(self._prepared)

    @property
    def fact_count(self) -> int:
        return len(self._prepared)

    def _score(self, prepared: tuple[Any, str, str], keywords: Sequence[str]) -> float:
        _, core, quote = prepared
        score = 0.0
        for keyword in keywords:
            token = _normalize(keyword)
            if len(token) < _MIN_KEYWORD_CHARS:
                continue
            if token in core:
                score += _CORE_WEIGHT
            elif token in quote:
                score += _QUOTE_WEIGHT
        return score

    async def retrieve(self, keywords: Sequence[str]) -> list[TextBlock]:
        """匹配并可复用的 TextBlock；无命中返回空列表（调用方据此退回实时检索）。"""
        if not self._prepared:
            return []
        tokens = [keyword for keyword in keywords if keyword]
        if not tokens:
            return []
        self.stats.queries += 1

        scored: list[tuple[float, float, Any]] = []
        for prepared in self._prepared:
            fact = prepared[0]
            score = self._score(prepared, tokens)
            if score <= 0:
                continue
            confidence = float(getattr(fact, "confidence", 0.0) or 0.0)
            bonus = _LOCKED_BONUS if getattr(fact, "locked", False) else 0.0
            scored.append((score + bonus, confidence, fact))
        if not scored:
            return []

        # 主序：匹配分（含锁定加成）；次序：置信度——同分时更可信的事实先进上下文
        scored.sort(key=lambda item: (item[0], item[1]), reverse=True)

        blocks: list[TextBlock] = []
        seen: set[tuple[str, str]] = set()
        counters: dict[str, int] = {}
        for _, _, fact in scored[: self._top_k]:
            document_name = str(getattr(fact, "document_name", "") or "知识库事实")
            file_id = f"{KB_FILE_PREFIX}{document_name}"
            text = str(getattr(fact, "quote", "") or getattr(fact, "value", "") or "").strip()
            if len(text) < 4:
                continue
            text = text[: self._max_text_chars]
            key = (file_id, text[:80])
            if key in seen:
                continue
            seen.add(key)
            index = counters.get(file_id, 0)
            counters[file_id] = index + 1
            blocks.append(TextBlock(file_id=file_id, page=1, index=index, text=text, kind="paragraph"))
            self.stats.sources[file_id] = document_name

        self.stats.hits += len(blocks)
        self.stats.matched_facts += min(len(scored), self._top_k)
        return blocks


__all__ = ["FactRetrievalStats", "FactRetriever", "MAX_FACT_TEXT_CHARS"]
