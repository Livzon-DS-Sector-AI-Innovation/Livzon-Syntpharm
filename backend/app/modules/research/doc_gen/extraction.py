"""槽位取值：检索候选资料块 → 调用内网模型 → 校验与依据回检。

这一层是「没有依据就不写」的落地点：模型输出必须通过 Pydantic 结构校验、
格式校验和证据回检（引用原文必须真的出现在解析文本里），否则一律降级为待补充。
"""

from __future__ import annotations

import asyncio
import difflib
import hashlib
import logging
import re
import unicodedata
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from app.core.llm import llm_client
from app.core.llm.exceptions import LLMOutputError, LLMProviderError, LLMRateLimitError
from app.modules.research.doc_gen import calc, status
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.prompts import build_extract_prompt, build_table_prompt
from app.modules.research.doc_gen.retrieval import BlockRetriever, score_text
from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], Awaitable[None]]
CancelProbe = Callable[[], bool]
_RETRY_CODES = (LLMProviderError, LLMRateLimitError, LLMOutputError)
_DATE_RE = re.compile(r"\d{4}\s*[-/年.]\s*\d{1,2}\s*[-/月.]\s*\d{1,2}")
_PERCENT_RE = re.compile(r"^\s*\d+(\.\d+)?\s*%\s*$")

# 证据回检：归一化后精确匹配失败时，允许按相似度模糊核对（容忍 OCR/排版差异）
_FUZZY_THRESHOLD = 0.9
_FUZZY_ANCHOR_LEN = 8  # 从引用中截取的定位片段长度
_FUZZY_FULLSCAN_LIMIT = 5000  # 归一化语料不超过该长度时允许全量滑窗兜底
# 宽检索兜底：主关键词 0 命中时把长词拆成相邻二字片段放宽召回
_WIDE_LIMIT_MULTIPLIER = 3
_WIDE_MAX_KEYWORDS = 24
# 项目登记结构化数据注入的虚拟文件前缀与角色：内容来自数据库而非解析文本，
# 本身即是权威事实，引用回检直接放行
DB_FILE_PREFIX = "db:"
DATABASE_ROLE = "database"
# 使用者手填的补充信息（新建报告弹窗第 5 行）：同样是一手信息，注入为虚拟文件
SUPPLEMENT_FILE_ID = "supplement"
SUPPLEMENT_ROLE = "supplement"
# 上一版报告正文（报告草稿）角色
DRAFT_ROLE = "report_draft"


def _normalize_text(text: str) -> str:
    """证据核对统一归一化：NFKC（全角→半角等）+ 小写 + 去全部空白。"""
    normalized = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", "", normalized)


def _widen_keywords(keywords: Sequence[str]) -> list[str]:
    """把中文长关键词拆成相邻二字片段（2-gram），用于 0 命中后的放宽检索。

    英文词按词边界匹配已经足够宽，不再拆分；片段数设上限防检索开销失控。
    """
    wide: list[str] = []
    for keyword in keywords:
        token = keyword.strip()
        if len(token) < 4 or token.isascii():
            continue
        for pos in range(len(token) - 1):
            gram = token[pos : pos + 2]
            if gram not in wide:
                wide.append(gram)
            if len(wide) >= _WIDE_MAX_KEYWORDS:
                return wide
    return wide


class ExtractionAbortError(Exception):
    """提取被强制终止（用户取消或任务整体超时）。

    上层（pipeline）捕获后转成任务级失败；它必须能穿透 ``_notify`` 的兜底 try，
    否则「进度回调里发现已取消」会被当成普通回调异常吞掉，取消就永远不生效。
    """

    def __init__(self, reason: str = "cancelled") -> None:
        super().__init__(reason)
        self.reason = reason


class EvidenceModel(BaseModel):
    """模型返回的单条依据。"""

    file_id: str = ""
    page: int = 1
    quote: str = ""


class SlotOut(BaseModel):
    """模型返回的单槽位结果。"""

    key: str
    value: Any = None
    found: bool = True
    confidence: float | None = None
    evidence: list[EvidenceModel] = Field(default_factory=list)
    candidates: list[Any] = Field(default_factory=list)


class ExtractOut(BaseModel):
    """批量抽取响应。"""

    slots: list[SlotOut] = Field(default_factory=list)


class TableOut(BaseModel):
    """表格行响应。"""

    rows: list[dict[str, Any]] = Field(default_factory=list)
    evidence: list[EvidenceModel] = Field(default_factory=list)


@dataclass(slots=True)
class SlotResult:
    """一个槽位的抽取结果。"""

    key: str
    text: str = ""
    # 成文前的文本（AI 报告生成会改写 text）：为空表示未成文
    pre_compose_text: str = ""
    rows: list[dict[str, str]] = field(default_factory=list)
    state: str = status.STATUS_OK
    reason: str = ""
    evidence: list[EvidenceModel] = field(default_factory=list)
    candidates: list[str] = field(default_factory=list)
    confidence: float | None = None


@dataclass(slots=True)
class ExtractStats:
    """抽取过程统计。"""

    calls: int = 0
    retries: int = 0
    failures: int = 0
    # 主关键词与宽检索兜底都未命中的槽位数（模型从未见到相关资料）
    retrieval_misses: int = 0
    # 已写入但模型置信度介于中/高阈值之间的槽位数（信息性统计，供人工抽查）
    low_confidence: int = 0
    # 辅助模型兜底成功的次数
    fallback_used: int = 0
    warnings: list[str] = field(default_factory=list)


class SlotExtractor:
    """按模板槽位从资料中取值。"""

    def __init__(
        self,
        spec: TemplateSpec,
        blocks: Sequence[TextBlock],
        *,
        roles_by_file: Mapping[str, Sequence[str]] | None = None,
        llm: Any = None,
        batch_size: int = 6,
        candidate_limit: int = 10,
        max_context_chars: int = 12000,
        max_retries: int = 3,
        confidence_high: float = 0.85,
        confidence_mid: float = 0.6,
        should_cancel: CancelProbe | None = None,
        call_timeout_seconds: float | None = None,
        model_override: str | None = None,
        config_name: str | None = None,
        max_concurrent_batches: int = 1,
        enable_cache: bool = False,
        vector_index: Any = None,
        vector_alpha: float = 0.6,
        embedding_model: str | None = None,
        fallback_model_override: str | None = None,
        fallback_config_name: str | None = None,
        file_analysis_context: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    ) -> None:
        self._spec = spec
        self._blocks = list(blocks)
        self._roles = dict(roles_by_file or {})
        self._llm = llm or llm_client
        self._model_override = model_override
        self._config_name = config_name
        self._fallback_model_override = fallback_model_override
        self._fallback_config_name = fallback_config_name
        self._batch_size = max(1, batch_size)
        self._candidate_limit = candidate_limit
        self._max_context_chars = max_context_chars
        self._max_retries = max(1, max_retries)
        self._confidence_high = confidence_high
        self._confidence_mid = confidence_mid
        self._should_cancel = should_cancel
        self._call_timeout = call_timeout_seconds
        self._max_concurrent_batches = max(1, max_concurrent_batches)
        self._vector_index = vector_index
        self._embedding_model = embedding_model
        self._retriever = BlockRetriever(self._blocks, vector_index=vector_index, vector_alpha=vector_alpha)
        by_file: dict[str, list[str]] = {}
        for block in self._blocks:
            by_file.setdefault(block.file_id, []).append(block.text)
        # 证据核对语料与引用做同样的归一化（NFKC + 小写 + 去空白），避免全半角差异误判
        self._by_file = {fid: _normalize_text("".join(parts)) for fid, parts in by_file.items()}
        self.stats = ExtractStats()
        # LLM 结果缓存：(slot_key, content_hash) → SlotResult，重跑时内容未变的槽位直接命中
        self._cache: dict[tuple[str, str], SlotResult] = {} if enable_cache else None  # type: ignore[assignment]
        self._cache_hits: int = 0
        # 文件分析预提取上下文：slot_key → [{file_id, file_name, content, relevance}]
        self._file_analysis_context: dict[str, list[dict[str, Any]]] = {
            k: [dict(item) for item in v] for k, v in (file_analysis_context or {}).items()
        }

    def _check_cancelled(self) -> None:
        """取消探针：在每个批次与每次模型调用的边界上检查。"""
        if self._should_cancel is not None and self._should_cancel():
            raise ExtractionAbortError("cancelled")

    async def run(
        self, on_progress: ProgressCallback | None = None, slots: Sequence[Slot] | None = None
    ) -> dict[str, SlotResult]:
        """跑槽位抽取。

        ``slots`` 为空时抽取整份模板；传入子集则只抽这些槽位——动态章节的局部槽位
        必须在实例化之后才知道有哪些，因此第二轮提取只能按子集跑。
        ``max_concurrent_batches > 1`` 时多批并发调用 LLM，加速提取阶段。
        """
        results: dict[str, SlotResult] = {}
        targets = list(slots) if slots is not None else list(self._spec.slots)
        simple = [s for s in targets if s.kind != "table" and not s.from_meta]
        tables = [s for s in targets if s.kind == "table" and not s.from_meta]
        total = len(simple) + len(tables)
        done = 0
        batches = self._batches(simple)

        if self._max_concurrent_batches <= 1:
            for batch in batches:
                self._check_cancelled()
                batch_results = await self._extract_batch(batch)
                results.update(batch_results)
                done += len(batch)
                await self._notify(on_progress, done, total)
        else:
            sem = asyncio.Semaphore(self._max_concurrent_batches)
            done_lock = asyncio.Lock()

            async def _run_batch(batch: list[Slot]) -> dict[str, SlotResult]:
                nonlocal done
                async with sem:
                    self._check_cancelled()
                    batch_results = await self._extract_batch(batch)
                async with done_lock:
                    done += len(batch)
                    await self._notify(on_progress, done, total)
                return batch_results

            batch_results_list = await asyncio.gather(*(_run_batch(b) for b in batches))
            for batch_results in batch_results_list:
                results.update(batch_results)

        # 表格槽位并行提取（受 extract_concurrency 信号量限制）
        if tables:
            table_sem = asyncio.Semaphore(max(1, self._max_concurrent_batches))
            table_done_lock = asyncio.Lock()

            async def _extract_table_guarded(slot: Slot) -> tuple[str, SlotResult]:
                async with table_sem:
                    self._check_cancelled()
                    result = await self._extract_table(slot)
                async with table_done_lock:
                    nonlocal done
                    done += 1
                    await self._notify(on_progress, done, total)
                return slot.key, result

            table_results = await asyncio.gather(*(_extract_table_guarded(s) for s in tables))
            for key, result in table_results:
                results[key] = result
        if self._cache is not None and self._cache_hits:
            logger.info("文档生成提取缓存命中", extra={"hits": self._cache_hits})
        return results

    async def _notify(self, on_progress: ProgressCallback | None, done: int, total: int) -> None:
        """进度回调失败不应中断抽取，但终止信号必须放行。"""
        if on_progress is None:
            return
        try:
            await on_progress(done, total)
        except (ExtractionAbortError, asyncio.CancelledError):
            raise
        except Exception:  # noqa: BLE001 - 进度写入失败仅记录
            logger.warning("文档生成进度回调失败", extra={"done": done, "total": total})

    def _allowed_files(self, slot: Slot) -> list[str] | None:
        """按槽位来源范围过滤可用文件。

        人工填写的报告内容（report_draft）不属于「资料/文献」任一来源角色，
        但它是使用者自己写的一手信息，因此对所有槽位始终可见。
        """
        if not self._roles:
            return None
        if set(slot.source_roles) == {"material", "literature"}:
            return None
        wanted = set(slot.source_roles)
        allowed = [fid for fid, roles in self._roles.items() if wanted & set(roles)]
        # 人工报告内容、项目登记数据、新建报告时填的补充信息都是一手权威信息，对所有槽位始终可见
        extras = [
            fid for fid, roles in self._roles.items() if {DRAFT_ROLE, DATABASE_ROLE, SUPPLEMENT_ROLE} & set(roles)
        ]
        return allowed + [fid for fid in extras if fid not in allowed]

    def _slot_keywords(self, slot: Slot) -> list[str]:
        """槽位检索词：label/key/query_hint 分词/别名/表格列名。"""
        keywords = [slot.label, slot.key]
        keywords += [w for w in re.split(r"[\s,、;；/]+", slot.query_hint) if len(w) >= 2]
        keywords += [term for term in slot.search_terms if term]
        for column in slot.columns:
            keywords.append(column.label or column.key)
        return [k for k in keywords if k]

    def _chunk_payload(self, chunks: Sequence[TextBlock]) -> list[dict[str, Any]]:
        return [{"file_id": c.file_id, "page": c.page, "text": c.text} for c in chunks]

    async def _candidates(self, slot: Slot) -> tuple[list[TextBlock], list[dict[str, Any]], bool]:
        """检索候选块，返回 (块, prompt 载荷, 是否走了宽检索兜底)。

        当向量索引可用时执行双路召回（关键词 + 向量融合），否则退化为纯关键词检索。
        主关键词 0 命中时不直接放弃：把中文长词拆成二字片段再检索一轮（宽检索），
        槽位用语与资料用语脱节时仍有机会召回；两轮都空才判定检索未命中。
        """
        keywords = self._slot_keywords(slot)
        allow_file_ids = self._allowed_files(slot)
        roles = self._roles or None

        # 向量索引可用时走双路召回
        if self._vector_index is not None and self._vector_index.is_built:
            query_text = " ".join(keywords)
            embed_fn = self._make_embed_fn()
            chunks = await self._retriever.candidates_with_vector(
                keywords,
                query_text=query_text,
                embed_fn=embed_fn,
                limit=self._candidate_limit,
                allow_file_ids=allow_file_ids,
                roles=roles,
            )
            if chunks:
                return chunks, self._chunk_payload(chunks), False
        else:
            # 纯关键词检索
            chunks = self._retriever.candidates(
                keywords, limit=self._candidate_limit, allow_file_ids=allow_file_ids, roles=roles
            )
            if chunks:
                return chunks, self._chunk_payload(chunks), False

        # 宽检索兜底
        wide = _widen_keywords(keywords)
        if wide:
            if self._vector_index is not None and self._vector_index.is_built:
                query_text = " ".join(wide)
                embed_fn = self._make_embed_fn()
                chunks = await self._retriever.candidates_with_vector(
                    wide,
                    query_text=query_text,
                    embed_fn=embed_fn,
                    limit=self._candidate_limit * _WIDE_LIMIT_MULTIPLIER,
                    allow_file_ids=allow_file_ids,
                    roles=roles,
                )
            else:
                chunks = self._retriever.candidates(
                    wide,
                    limit=self._candidate_limit * _WIDE_LIMIT_MULTIPLIER,
                    allow_file_ids=allow_file_ids,
                    roles=roles,
                )
            if chunks:
                return chunks, self._chunk_payload(chunks), True
        return [], [], False

    def _make_embed_fn(self) -> Callable[[list[str]], Awaitable[list[list[float]]]]:
        """构造 embedding 函数，供向量检索使用。"""

        async def _embed(texts: list[str]) -> list[list[float]]:
            return await self._llm.embed(texts, model_override=self._embedding_model)

        return _embed

    def _batches(self, slots: Sequence[Slot]) -> list[list[Slot]]:
        """按来源范围分组切批：不同 source_roles 的槽位不共享上下文，防止文献污染材料槽位。"""
        groups: dict[tuple[str, ...], list[Slot]] = {}
        for slot in slots:
            groups.setdefault(tuple(sorted(slot.source_roles)), []).append(slot)
        batches: list[list[Slot]] = []
        for group in groups.values():
            for start in range(0, len(group), self._batch_size):
                batches.append(group[start : start + self._batch_size])
        return batches

    async def _extract_batch(self, slots: Sequence[Slot]) -> dict[str, SlotResult]:
        """一次调用抽取多个简单槽位。"""
        payload_slots: list[dict[str, Any]] = []
        pool: list[dict[str, Any]] = []
        active: list[Slot] = []
        skipped: dict[str, SlotResult] = {}
        # 缓存命中：slot_key → 候选内容哈希，命中时跳过 LLM 调用
        cached_results: dict[str, SlotResult] = {}
        # 预检索所有槽位的候选块：先过滤 manual_only，再并行检索候选
        slot_chunks: dict[str, tuple[list[TextBlock], list[dict[str, Any]], bool]] = {}
        need_retrieval: list[Slot] = []
        for slot in slots:
            if slot.manual_only:
                skipped[slot.key] = SlotResult(
                    key=slot.key, text=status.pending("需人工填写"), state=status.STATUS_MANUAL
                )
                continue
            need_retrieval.append(slot)

        # 并行检索所有槽位的候选块（关键词/向量检索 IO 密集，并行显著提速）
        if need_retrieval:
            retrieval_results = await asyncio.gather(*(self._candidates(s) for s in need_retrieval))
            for slot, (chunks, chunk_payload, wide) in zip(need_retrieval, retrieval_results):
                slot_chunks[slot.key] = (chunks, chunk_payload, wide)
                if not chunks:
                    self.stats.retrieval_misses += 1
                    skipped[slot.key] = SlotResult(
                        key=slot.key, text=status.pending("资料中未找到相关内容"), state=status.STATUS_PENDING
                    )
                    continue
                # 缓存检查：内容未变的槽位直接复用上次结果
                if self._cache is not None:
                    content_hash = self._content_hash(chunks)
                    cached = self._cache.get((slot.key, content_hash))
                    if cached is not None:
                        cached_results[slot.key] = cached
                        self._cache_hits += 1
                        continue
                payload_slots.append(_slot_payload(slot))
                active.append(slot)
                for item in chunk_payload:
                    if item not in pool:
                        pool.append(item)
        if not payload_slots:
            return {**skipped, **cached_results}
        # 上下文预算内贪心挑选：按本批槽位关键词并集给候选块打分，高分块优先进入 prompt
        batch_keywords = sorted({kw for slot in active for kw in self._slot_keywords(slot)})
        pattern_cache: dict[str, re.Pattern[str]] = {}
        pool_scores = [score_text(str(item["text"]), batch_keywords, pattern_cache) for item in pool]
        # 构建文件分析预提取提示：为每个槽位提供预提取内容参考
        file_analysis_hints: dict[str, str] = {}
        for slot in active:
            fa_items = self._file_analysis_context.get(slot.key)
            if fa_items:
                # 取最相关的前 2 个文件的预提取内容
                hints = [item.get("content", "")[:150] for item in fa_items[:2] if item.get("content")]
                if hints:
                    file_analysis_hints[slot.key] = "；".join(hints)
        outputs = await self._call_json(
            build_extract_prompt(
                payload_slots, pool, self._max_context_chars, pool_scores,
                file_analysis_hints=file_analysis_hints or None,
            ),
            expected_keys=["slots"],
        )
        results = {**skipped, **cached_results}
        by_key = {out.key: out for out in outputs.slots} if outputs else {}
        for slot in slots:
            if slot.key in results:
                continue
            result = self._finalize_slot(slot, by_key.get(slot.key))
            results[slot.key] = result
            # 缓存存储：只缓存有明确结果（OK/NEEDS_VERIFY）的槽位
            if self._cache is not None and result.state in (status.STATUS_OK, status.STATUS_NEEDS_VERIFY):
                cached_data = slot_chunks.get(slot.key)
                if cached_data:
                    chunks = cached_data[0]
                    content_hash = self._content_hash(chunks)
                    self._cache[(slot.key, content_hash)] = result
        return results

    @staticmethod
    def _content_hash(chunks: Sequence[TextBlock]) -> str:
        """对候选块内容计算摘要，用于缓存 key。"""
        h = hashlib.sha256()
        for chunk in chunks:
            h.update(f"{chunk.file_id}:{chunk.page}:{chunk.text}".encode())
        return h.hexdigest()[:16]

    def _split_evidence(self, evidence: Sequence[EvidenceModel]) -> tuple[list[EvidenceModel], list[EvidenceModel]]:
        """按核对结果把依据分成 (精确命中, 模糊命中)。"""
        exact: list[EvidenceModel] = []
        fuzzy: list[EvidenceModel] = []
        for item in evidence:
            verified, is_fuzzy = self._verify_quote(item)
            if not verified:
                continue
            (fuzzy if is_fuzzy else exact).append(item)
        return exact, fuzzy

    def _finalize_slot(self, slot: Slot, out: SlotOut | None) -> SlotResult:
        """校验单个填充项输出。

        依据核对分级处理：
        - 精确命中 → 正常落地；
        - 仅模糊命中 → 值照常写入，但标 needs_verify 提示人工核对（大概率只是排版/OCR 差异）；
        - 完全无法核对 → 正文不写入（占位待补充），但把 AI 给出的值与候选保留下来供人工参考，不再丢弃。
        """
        if out is None:
            return SlotResult(
                key=slot.key, text=status.pending("AI 未返回该填充项结果"), state=status.STATUS_FAILED
            )
        value = str(out.value or "").strip()
        if not out.found or not value:
            return SlotResult(key=slot.key, text=status.pending("资料中未找到依据"), state=status.STATUS_PENDING)
        exact, fuzzy = self._split_evidence(out.evidence)
        if not exact and not fuzzy:
            if slot.draft_allowed:
                return SlotResult(
                    key=slot.key,
                    text=status.with_draft_prefix(value),
                    state=status.STATUS_DRAFT,
                    reason="引用未能核对，需人工确认",
                    candidates=[str(c) for c in out.candidates],
                    confidence=out.confidence,
                )
            alternatives = [value, *[str(c) for c in out.candidates]]
            return SlotResult(
                key=slot.key,
                text=status.pending("依据无法在原文中定位"),
                state=status.STATUS_PENDING,
                reason="引用未能核对，AI 候选值见生成说明",
                candidates=[c for c in alternatives if c.strip()],
                evidence=list(out.evidence),
                confidence=out.confidence,
            )
        if fuzzy and not exact:
            return SlotResult(
                key=slot.key,
                text=value,
                state=status.STATUS_NEEDS_VERIFY,
                reason="引用经模糊匹配核对（存在排版/识别差异），请人工确认",
                evidence=fuzzy,
                confidence=out.confidence,
            )
        candidates = [str(c) for c in out.candidates if str(c).strip() and str(c).strip() != value]
        if candidates:
            return SlotResult(
                key=slot.key,
                text=status.CONFLICT_MARK,
                state=status.STATUS_CONFLICT,
                reason="不同资料给出的值不一致",
                evidence=[*exact, *fuzzy],
                candidates=[value, *candidates],
                confidence=out.confidence,
            )
        format_error = _format_error(slot, value)
        if format_error:
            return SlotResult(key=slot.key, text=status.pending(format_error), state=status.STATUS_PENDING)
        return self._grade_confidence(
            SlotResult(
                key=slot.key, text=value, state=status.STATUS_OK, evidence=exact, confidence=out.confidence
            )
        )

    def _grade_confidence(self, result: SlotResult) -> SlotResult:
        """置信度分级：模型自报置信度过低时把「已填充」降级为需人工核对。

        - confidence < mid：值虽写入，但降级为 needs_verify，理由写明置信度；
        - mid ≤ confidence < high：保持已填充，计入 low_confidence 统计供抽查；
        - 未返回置信度（None）或非 OK 状态不做处理。
        """
        if result.confidence is None or result.state != status.STATUS_OK:
            return result
        if result.confidence < self._confidence_mid:
            result.state = status.STATUS_NEEDS_VERIFY
            result.reason = f"模型置信度较低（{result.confidence:.0%}），请人工确认"
            return result
        if result.confidence < self._confidence_high:
            self.stats.low_confidence += 1
        return result

    def _corpus_of(self, file_id: str) -> str:
        """取某份资料的归一化语料；file_id 未知时退回全部语料拼接。"""
        haystack = self._by_file.get(file_id)
        if haystack is None:
            haystack = "".join(self._by_file.values())
        return haystack

    def _verify_quote(self, evidence: EvidenceModel) -> tuple[bool, bool]:
        """证据回检，返回 (是否核对通过, 是否模糊命中)。

        两级策略：
        1. 归一化（NFKC + 小写 + 去空白）后精确子串匹配；
        2. 失败时先取引用的锚点片段定位再局部比对相似度，语料较短时全量滑窗兜底，
           相似度达标视为「模糊命中」（值可信但引用存在排版/OCR 级差异，需人工确认）。

        项目登记数据（db: 前缀虚拟文件）来自数据库权威记录而非解析文本，
        本身即是事实来源，直接视为精确核对通过。
        """
        if evidence.file_id.startswith(DB_FILE_PREFIX):
            return True, False
        needle = _normalize_text(evidence.quote)
        if len(needle) < 4:
            return False, False
        haystack = self._corpus_of(evidence.file_id)
        if needle in haystack:
            return True, False
        return self._fuzzy_locate(needle, haystack)

    def _fuzzy_locate(self, needle: str, haystack: str) -> tuple[bool, bool]:
        """相似度回检：锚点片段定位 + 等长窗口比对，避免大语料上的全量滑窗。

        窗口长度与引用一致（长度不等会稀释 SequenceMatcher 比率），在锚点给出的
        理想对齐位置附近做小偏移扫描；锚点全部落空且语料较短时才全量滑窗兜底。
        """
        length = len(needle)
        starts: list[int] = []
        pos = haystack.find(needle[:_FUZZY_ANCHOR_LEN])
        if pos >= 0:
            starts.append(pos)
        pos = haystack.find(needle[-_FUZZY_ANCHOR_LEN:])
        if pos >= 0:
            starts.append(pos - (length - _FUZZY_ANCHOR_LEN))
        if not starts and length >= 2 * _FUZZY_ANCHOR_LEN:
            mid_start = length // 2 - _FUZZY_ANCHOR_LEN // 2
            pos = haystack.find(needle[mid_start:][: _FUZZY_ANCHOR_LEN])
            if pos >= 0:
                starts.append(pos - mid_start)
        if not starts:
            if len(haystack) > _FUZZY_FULLSCAN_LIMIT:
                return False, False
            step = max(length // 4, 1)
            starts = list(range(0, max(len(haystack) - length + 1, 1), step))
        for start in starts:
            for delta in (-4, -2, 0, 2, 4):
                left = start + delta
                if left < 0:
                    continue
                candidate = haystack[left : left + length]
                if len(candidate) < length:
                    continue
                if difflib.SequenceMatcher(None, needle, candidate, autojunk=False).ratio() >= _FUZZY_THRESHOLD:
                    return True, True
        return False, False

    async def _extract_table(self, slot: Slot) -> SlotResult:
        """表格槽位：逐行抽取，计算列与序号交给程序。"""
        if slot.manual_only:
            return SlotResult(key=slot.key, state=status.STATUS_MANUAL, reason="需人工填写")
        chunks, pool, _wide = await self._candidates(slot)
        if not chunks:
            return SlotResult(key=slot.key, state=status.STATUS_PENDING, reason="资料中未找到相关表格数据")
        payload = _slot_payload(slot)
        writable = [c for c in payload["columns"] if c.get("writable")]
        if not writable:
            return SlotResult(key=slot.key, state=status.STATUS_MANUAL, reason="该表所有列均为程序计算")
        # 上下文预算内贪心挑选：按本槽位关键词给候选块打分
        pattern_cache: dict[str, re.Pattern[str]] = {}
        chunk_scores = [score_text(c.text, self._slot_keywords(slot), pattern_cache) for c in chunks]
        outputs = await self._call_json(
            build_table_prompt(payload, pool, self._max_context_chars, chunk_scores),
            model=TableOut,
            expected_keys=["rows"],
        )
        rows: list[dict[str, str]] = []
        evidence: list[EvidenceModel] = []
        raw_rows = outputs.rows if outputs else []
        for item in raw_rows:
            values = item.get("values") if isinstance(item, dict) else None
            if not isinstance(values, dict):
                continue
            record: dict[str, str] = {}
            seq_key = slot.table.sequence_column if slot.table else None
            for column in slot.columns:
                if column.compute != "none" or column.key == seq_key:
                    continue
                raw = values.get(column.key)
                if raw is None:
                    continue
                text = str(raw).strip()
                if not text:
                    continue
                if len(text) > column.max_chars:
                    text = text[: column.max_chars]
                record[column.key] = text
            if record and any(v for v in record.values()):
                rows.append(record)
            for raw_evidence in item.get("evidence", []) if isinstance(item, dict) else []:
                model = _to_evidence(raw_evidence)
                if model and self._verify_quote(model)[0]:
                    evidence.append(model)
        limit = slot.table.row_limit if slot.table else 60
        truncated = len(rows) > limit
        rows = rows[:limit]
        if not rows:
            return SlotResult(
                key=slot.key, state=status.STATUS_PENDING, reason="资料中未找到表格数据", evidence=evidence
            )
        state = status.STATUS_OVERFLOW if truncated else status.STATUS_OK
        reason = f"行数超过模板原件可承载上限 {limit}，已截断" if truncated else ""
        return SlotResult(key=slot.key, rows=rows, state=state, reason=reason, evidence=evidence)

    async def _call_json(
        self,
        messages: list[dict[str, str]],
        model: type[BaseModel] = ExtractOut,
        expected_keys: list[str] | None = None,
    ) -> Any:
        """带重试与降级的模型调用；返回校验后的模型实例，失败返回 None。

        主模型（快模型）重试失败后，用辅助模型（强模型）再试一次——「快模型跑量，强模型兜底」。
        单次调用套一层 ``wait_for`` 硬超时：模型端点不返回时 httpx 的读超时并不总能把
        协程叫醒（连接已建立但流被挂住），任务就会永久停在「AI 分析资料」且取消不掉。
        """
        last_error = ""
        # 第一阶段：主模型重试
        for attempt in range(self._max_retries):
            self._check_cancelled()
            try:
                raw = await self._invoke(messages, expected_keys, use_fallback=False)
                self.stats.calls += 1
                return model.model_validate(raw)
            except (ExtractionAbortError, asyncio.CancelledError):
                raise
            except TimeoutError:
                last_error = "调用超时"
                self.stats.retries += 1
                logger.warning(
                    "文档生成主模型调用超时，重试",
                    extra={"attempt": attempt + 1, "timeout": self._call_timeout},
                )
            except _RETRY_CODES as exc:
                last_error = type(exc).__name__
                self.stats.retries += 1
                logger.warning("文档生成主模型调用失败，重试", extra={"attempt": attempt + 1, "error": last_error})
            except ValidationError as exc:
                last_error = "输出结构不符合约定"
                self.stats.retries += 1
                logger.warning(
                    "文档生成主模型输出校验失败",
                    extra={"attempt": attempt + 1, "errors": len(exc.errors())},
                )
            except Exception as exc:  # noqa: BLE001 - 网络类异常种类多，统一降级
                last_error = type(exc).__name__
                self.stats.retries += 1
                logger.warning("文档生成主模型调用异常", extra={"attempt": attempt + 1, "error": last_error})
            if attempt + 1 < self._max_retries:
                await asyncio.sleep(2**attempt)

        # 第二阶段：辅助模型兜底（如果配置了）
        if self._fallback_model_override or self._fallback_config_name:
            logger.info("主模型重试失败，切换辅助模型兜底", extra={"error": last_error})
            for attempt in range(self._max_retries):
                self._check_cancelled()
                try:
                    raw = await self._invoke(messages, expected_keys, use_fallback=True)
                    self.stats.calls += 1
                    self.stats.fallback_used += 1
                    logger.info("辅助模型兜底成功", extra={"attempt": attempt + 1})
                    return model.model_validate(raw)
                except (ExtractionAbortError, asyncio.CancelledError):
                    raise
                except TimeoutError:
                    last_error = "辅助模型调用超时"
                    self.stats.retries += 1
                    logger.warning("文档生成辅助模型调用超时，重试", extra={"attempt": attempt + 1})
                except _RETRY_CODES as exc:
                    last_error = type(exc).__name__
                    self.stats.retries += 1
                    logger.warning(
                        "文档生成辅助模型调用失败，重试",
                        extra={"attempt": attempt + 1, "error": last_error},
                    )
                except ValidationError as exc:
                    last_error = "辅助模型输出校验失败"
                    self.stats.retries += 1
                    logger.warning(
                        "文档生成辅助模型输出校验失败",
                        extra={"attempt": attempt + 1, "errors": len(exc.errors())},
                    )
                except Exception as exc:
                    last_error = type(exc).__name__
                    self.stats.retries += 1
                    logger.warning("文档生成辅助模型调用异常", extra={"attempt": attempt + 1, "error": last_error})
                if attempt + 1 < self._max_retries:
                    await asyncio.sleep(2**attempt)

        self.stats.failures += 1
        self.stats.warnings.append(f"模型调用降级：{last_error}")
        logger.error("文档生成模型调用最终失败，按降级处理", extra={"error": last_error})
        return None

    async def _invoke(
        self, messages: list[dict[str, str]], expected_keys: list[str] | None, use_fallback: bool = False
    ) -> Any:
        """执行一次模型调用，必要时施加硬超时。use_fallback=True 时用辅助模型。"""
        if use_fallback:
            model_override = self._fallback_model_override
            config_name = self._fallback_config_name
        else:
            model_override = self._model_override
            config_name = self._config_name
        call = self._llm.chat_json(
            messages,
            expected_keys=expected_keys,
            temperature=0,
            model_override=model_override,
            config_name=config_name,
        )
        if self._call_timeout is None or self._call_timeout <= 0:
            return await call
        return await asyncio.wait_for(call, timeout=self._call_timeout)


def _slot_payload(slot: Slot) -> dict[str, Any]:
    """把槽位定义转成 prompt 可用的字典。"""
    sequence_key = slot.table.sequence_column if slot.table else None
    return {
        "key": slot.key,
        "label": slot.label,
        "expects": slot.expects,
        "max_chars": slot.max_chars,
        "required": slot.required,
        "draft_allowed": slot.draft_allowed,
        "query_hint": slot.query_hint,
        "columns": [
            {
                "key": c.key,
                "label": c.label or c.key,
                "max_chars": c.max_chars,
                "writable": c.compute == "none" and c.key != sequence_key,
            }
            for c in slot.columns
        ],
    }


def _to_evidence(raw: Any) -> EvidenceModel | None:
    """宽容地解析模型返回的依据对象。"""
    if isinstance(raw, EvidenceModel):
        return raw
    if isinstance(raw, dict):
        try:
            return EvidenceModel.model_validate(raw)
        except ValidationError:
            return None
    return None


def _format_error(slot: Slot, value: str) -> str:
    """值格式校验。"""
    if slot.expects == "number" and calc.to_number(value) is None:
        return "数值格式不符"
    if slot.expects == "date" and not _DATE_RE.search(value):
        return "日期格式不符"
    if slot.expects == "percent" and not _PERCENT_RE.match(value):
        return "百分比格式不符"
    return ""
