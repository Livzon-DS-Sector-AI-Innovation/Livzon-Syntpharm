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
from app.modules.research.doc_gen import calc, gap, status
from app.modules.research.doc_gen.kb_retrieval import KB_FILE_PREFIX, KB_POOL_PRIORITY
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.prompts import build_extract_prompt, build_probe_prompt, build_table_prompt
from app.modules.research.doc_gen.retrieval import BlockRetriever, score_text
from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec

logger = logging.getLogger(__name__)

ProgressCallback = Callable[[int, int], Awaitable[None]]
CancelProbe = Callable[[], bool]
_RETRY_CODES = (LLMProviderError, LLMRateLimitError, LLMOutputError)
_DATE_RE = re.compile(r"\d{4}\s*[-/年.]\s*\d{1,2}\s*[-/月.]\s*\d{1,2}")
_PERCENT_RE = re.compile(r"^\s*\d+(\.\d+)?\s*%\s*$")
# 引用编号复核用：数字片段（含小数），单字符噪声太大在调用处过滤
_NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")

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
# 项目知识库召回片段（file_id 带 kb: 前缀）角色：项目沉淀的权威资料，对所有槽位可见
KNOWLEDGE_ROLE = "knowledge"
# 检索口径：默认口径以槽位关键词为主、宽检索仅在前者 0 命中时兜底；
# 缺口重试口径把宽检索词（长词拆成的二字片段）当主口径，换一套词重新召回一轮。
RETRIEVAL_DEFAULT = "default"
RETRIEVAL_RECALL = "recall"


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
    # 模型自报的引用编号：对应 prompt 里 [资料 N]，指向候选数组下标 + 1
    refs: list[int] = Field(default_factory=list)
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
    # 未填上时的结构化归因（``gap.GAP_*``）：空字符串表示已填充或未归因。
    # 产出结果时当场标注，供缺口闭环决定是否值得重试——不靠猜 reason 文案。
    gap_reason: str = ""


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
    # 项目知识库贡献的候选片段数（0 表示未接入知识库或全部未命中）
    kb_hits: int = 0
    # 取值与槽位需求描述（量纲/允许取值）不符、被降级为需人工核对的槽位数
    requirement_mismatches: int = 0
    # 引用文本未能核对、但按模型自报的资料编号可定位取值而被保留的槽位数
    refs_rescued: int = 0
    # 表格槽位里没有任何可核对依据的数据行数（行照写但整表降级为需人工核对）
    table_rows_unverified: int = 0
    warnings: list[str] = field(default_factory=list)


def merge_stats(target: ExtractStats, source: ExtractStats) -> None:
    """把一次附加抽取（缺口重试）的统计并入主统计对象。

    重试是额外发生的模型调用与知识库召回，账必须记在全量上，否则 ``job.stats``
    里的失败率与召回缺口会低于实际值。
    """
    target.calls += source.calls
    target.retries += source.retries
    target.failures += source.failures
    target.retrieval_misses += source.retrieval_misses
    target.low_confidence += source.low_confidence
    target.fallback_used += source.fallback_used
    target.kb_hits += source.kb_hits
    target.requirement_mismatches += source.requirement_mismatches
    target.refs_rescued += source.refs_rescued
    target.table_rows_unverified += source.table_rows_unverified
    target.warnings.extend(source.warnings)


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
        persist_cache: Any = None,
        vector_index: Any = None,
        vector_alpha: float = 0.6,
        embedding_model: str | None = None,
        fallback_model_override: str | None = None,
        fallback_config_name: str | None = None,
        file_analysis_context: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
        kb_retriever: Any = None,
        fact_retriever: Any = None,
        retrieval_profile: str = RETRIEVAL_DEFAULT,
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
        # 跨任务持久缓存（DB 版，鸭子类型：key()/get()/put()）：为空则只用进程内缓存
        self._persist_cache = persist_cache
        self._cache_hits: int = 0
        # 文件分析预提取上下文：slot_key → [{file_id, file_name, content, relevance}]
        self._file_analysis_context: dict[str, list[dict[str, Any]]] = {
            k: [dict(item) for item in v] for k, v in (file_analysis_context or {}).items()
        }
        # 项目知识库召回器（可选）：按槽位即时召回，命中片段作为虚拟资料参与 prompt 与回检
        self._kb_retriever = kb_retriever
        # 本地事实库召回器（可选）：知识库候选的第一级来源，零外部调用；无命中时回落实时检索
        self._fact_retriever = fact_retriever
        # 检索口径：缺口重试轮用 recall（宽检索词当主口径），常规轮用默认口径
        self._retrieval_profile = retrieval_profile
        # 知识库命中片段的原文：file_id → [片段文本]，供证据回检按文件取语料
        self._kb_raw: dict[str, list[str]] = {}
        self._kb_files: set[str] = set()

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
        # 知识库命中片段不参与本地检索（不在 self._blocks 里），但必须放行白名单，
        # 否则受限来源的槽位会在合并候选时被过滤掉知识库贡献
        merged = allowed + [fid for fid in extras if fid not in allowed]
        return merged + [fid for fid in sorted(self._kb_files) if fid not in merged]

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

    async def _kb_candidates(self, keywords: Sequence[str]) -> list[TextBlock]:
        """项目知识库候选（可选来源）：本地事实库优先，RAGFlow 实时召回兜底。

        两级来源的产出同构（都是 ``file_id = "kb:..."`` 的虚拟资料），这里统一登记进
        ``_kb_raw``：证据回检按 file_id 取语料，必须能查到这些片段，否则模型引用知识库
        内容会被判成「无依据」而误降级。

        事实库是「先榨一遍全库」的产物，零外部调用、覆盖不受查询词限制；它在某个槽位上
        无命中时才回落到按槽位实时检索（远端更贵，只作兜底）。
        """
        blocks = await self._fact_candidates(keywords)
        if not blocks:
            blocks = await self._live_kb_candidates(keywords)
        for block in blocks:
            self._kb_raw.setdefault(block.file_id, []).append(block.text)
            self._kb_files.add(block.file_id)
        self.stats.kb_hits += len(blocks)
        return list(blocks)

    async def _fact_candidates(self, keywords: Sequence[str]) -> list[TextBlock]:
        """本地事实库召回（零外部调用）；未接入事实库时返回空列表。"""
        if self._fact_retriever is None:
            return []
        try:
            return list(await self._fact_retriever.retrieve(keywords))
        except Exception:  # noqa: BLE001 - 事实库不可用只降级，绝不影响提取
            logger.exception("事实库召回异常，回落到实时知识库检索")
            return []

    async def _live_kb_candidates(self, keywords: Sequence[str]) -> list[TextBlock]:
        """RAGFlow 实时召回（兜底）；未接入或服务异常时返回空列表。"""
        if self._kb_retriever is None:
            return []
        try:
            return list(await self._kb_retriever.retrieve(keywords))
        except Exception:  # noqa: BLE001 - 外部服务异常面广，统一降级为「本次无知识库资料」
            logger.exception("知识库召回异常，本次仅用本地资料")
            return []

    def _merge_candidates(self, kb_chunks: Sequence[TextBlock], local_chunks: Sequence[TextBlock]) -> list[TextBlock]:
        """知识库命中在前、本地检索补足；按 (文件, 内容前缀) 去重。

        知识库片段是外部检索服务按语义挑出的 top-k，数量可控；
        本地候选仍按原有 limit 竞争，两者不互相挤占名额。
        """
        merged: list[TextBlock] = []
        seen: set[tuple[str, str]] = set()
        for block in list(kb_chunks) + list(local_chunks):
            key = (block.file_id, block.text[:80])
            if key in seen:
                continue
            seen.add(key)
            merged.append(block)
        return merged

    async def _candidates(self, slot: Slot) -> tuple[list[TextBlock], list[dict[str, Any]], bool]:
        """检索候选块，返回 (块, prompt 载荷, 是否走了宽检索兜底)。

        候选有两路来源：项目知识库（按槽位即时召回）与本地资料（关键词 / 向量双路召回）。
        当向量索引可用时执行双路召回（关键词 + 向量融合），否则退化为纯关键词检索。
        主关键词 0 命中时不直接放弃：把中文长词拆成二字片段再检索一轮（宽检索），
        槽位用语与资料用语脱节时仍有机会召回；两轮都空才判定检索未命中。
        """
        keywords = self._slot_keywords(slot)
        if self._retrieval_profile == RETRIEVAL_RECALL:
            # 缺口重试口径：主口径已经试过且失败了，再用同一套词只会拿到同一批结果
            # （知识库召回器按查询词缓存，更是原样返回）。把长词拆成二字片段当主口径，
            # 本地检索与知识库召回都变成「另一次查询」，才有机会捞到措辞不同的资料。
            keywords = _widen_keywords(keywords) or keywords
        allow_file_ids = self._allowed_files(slot)
        roles = self._roles or None
        kb_chunks = await self._kb_candidates(keywords)
        # 需求描述声明「取值来源只允许项目知识库」时，本地资料与登记数据不得进入候选
        kb_only = slot.source_scope == "project_kb"

        # 向量索引可用时走双路召回
        if kb_only:
            chunks: list[TextBlock] = []
        elif self._vector_index is not None and self._vector_index.is_built:
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
        else:
            # 纯关键词检索
            chunks = self._retriever.candidates(
                keywords, limit=self._candidate_limit, allow_file_ids=allow_file_ids, roles=roles
            )
        merged = self._merge_candidates(kb_chunks, chunks)
        if merged:
            return merged, self._chunk_payload(merged), False
        if kb_only:
            # 来源受限的槽位不做宽检索兜底：兜底会引入项目材料，违背 source_scope
            return [], [], False

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
            merged = self._merge_candidates(kb_chunks, chunks)
            if merged:
                return merged, self._chunk_payload(merged), True
        return [], [], False

    def _make_embed_fn(self) -> Callable[[list[str]], Awaitable[list[list[float]]]]:
        """构造 embedding 函数，供向量检索使用。"""

        async def _embed(texts: list[str]) -> list[list[float]]:
            return await self._llm.embed(texts, model_override=self._embedding_model)

        return _embed

    def _batches(self, slots: Sequence[Slot]) -> list[list[Slot]]:
        """按来源范围分组、再按章节对齐切批。

        分组防污染：不同 source_roles 的槽位不共享上下文，防止文献污染材料槽位。
        章节对齐：模板分析给出的 ``Slot.section`` 让同章槽位尽量留在同一批（共享上下文、
        行文衔接），但不强制在章节边界切分——只有当前批已够大（≥ 批大小的一半）时才在
        章节变化处收口，避免「一章只有一两个槽位」把批切碎反而增加调用次数。
        """
        groups: dict[tuple[str, ...], list[Slot]] = {}
        for slot in slots:
            groups.setdefault(tuple(sorted(slot.source_roles)), []).append(slot)
        batches: list[list[Slot]] = []
        for group in groups.values():
            batches.extend(self._section_batches(group))
        return batches

    def _section_batches(self, group: Sequence[Slot]) -> list[list[Slot]]:
        """章节对齐的分批；无章节信息（旧模板/分析未产出）时退回原顺序切批。"""
        size = max(1, self._batch_size)
        if not any(slot.section for slot in group):
            return [list(group[start : start + size]) for start in range(0, len(group), size)]
        batches: list[list[Slot]] = []
        batch: list[Slot] = []
        for slot in group:
            if batch and (len(batch) >= size or (slot.section != batch[0].section and len(batch) >= max(1, size // 2))):
                batches.append(batch)
                batch = []
            batch.append(slot)
        if batch:
            batches.append(batch)
        return batches

    async def probe(self, slots: Sequence[Slot]) -> dict[str, SlotResult]:
        """定向补问：对「有候选却没填上」的缺口槽位做一次聚焦问询（一次调用处理全部目标）。

        与批量抽取的区别：目标少、每个槽位只带自己的候选资料（编号 [资料 N] 与批量口径
        一致）、指令收窄到「只判断这些槽位」——用于找回在批量 prompt 里被漏看的取值。
        这里只负责产出候选结果，优劣由调用方判定（同缺口闭环的纪律：只接受确有提升的结果）。
        """
        # 护栏：表格槽位有专门的行抽取路径（_extract_table，返回值在 rows 里），
        # 绝不能走「批量/定向补问」的文本通道——否则会产出字符串值并可能覆盖行数据
        targets: list[Slot] = [slot for slot in slots if not slot.manual_only and slot.kind != "table"]
        if not targets:
            return {}
        fetched = await asyncio.gather(*(self._candidates(slot) for slot in targets))
        prompt_slots: list[dict[str, Any]] = []
        pools: dict[str, list[dict[str, Any]]] = {}
        for slot, (chunks, payload, _wide) in zip(targets, fetched):
            if not chunks:
                continue
            prompt_slots.append(_slot_payload(slot))
            pools[slot.key] = list(payload)
        if not prompt_slots:
            return {}
        outputs = await self._call_json(
            build_probe_prompt(prompt_slots, pools, self._max_context_chars),
            expected_keys=["slots"],
        )
        by_key = {out.key: out for out in outputs.slots} if outputs else {}
        results: dict[str, SlotResult] = {}
        for slot in targets:
            out = by_key.get(slot.key)
            if out is None:
                continue
            results[slot.key] = self._finalize_slot(slot, out, pools.get(slot.key))
        return results

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
                    key=slot.key,
                    text=status.pending("需人工填写"),
                    state=status.STATUS_MANUAL,
                    gap_reason=gap.GAP_MANUAL,
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
                        key=slot.key,
                        text=status.pending("资料中未找到相关内容"),
                        state=status.STATUS_PENDING,
                        gap_reason=gap.GAP_NO_MATERIAL,
                    )
                    continue
                # 缓存检查：内容未变的槽位直接复用上次结果（进程内 → 跨任务两级）
                cached = await self._cache_lookup(slot, chunks)
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
        # 知识库命中片段加固定权重：它们是外部检索服务按语义精选出的结果，
        # 应按召回顺序优先进入上下文；本地「多次关键词命中」的强相关块仍可排在前面
        pool_scores = [
            score_text(str(item["text"]), batch_keywords, pattern_cache)
            + (KB_POOL_PRIORITY if str(item.get("file_id", "")).startswith(KB_FILE_PREFIX) else 0.0)
            for item in pool
        ]
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
                payload_slots,
                pool,
                self._max_context_chars,
                pool_scores,
                file_analysis_hints=file_analysis_hints or None,
            ),
            expected_keys=["slots"],
        )
        results = {**skipped, **cached_results}
        by_key = {out.key: out for out in outputs.slots} if outputs else {}
        for slot in slots:
            if slot.key in results:
                continue
            result = self._finalize_slot(slot, by_key.get(slot.key), pool)
            results[slot.key] = result
            # 缓存存储：只缓存有明确结果（OK/NEEDS_VERIFY）的槽位
            cached_data = slot_chunks.get(slot.key)
            if cached_data:
                await self._cache_store(slot, cached_data[0], result)
        return results

    async def _cache_lookup(self, slot: Slot, chunks: Sequence[TextBlock]) -> SlotResult | None:
        """两级缓存读取：进程内（任务内命中）→ 跨任务持久缓存（DB）。"""
        if self._cache is None and self._persist_cache is None:
            return None
        content_hash = self._content_hash(chunks)
        if self._cache is not None:
            cached = self._cache.get((slot.key, content_hash))
            if cached is not None:
                return cached
        if self._persist_cache is not None:
            cached = await self._persist_cache.get(self._persist_cache.key(slot.key, content_hash))
            restored: SlotResult | None = cached if isinstance(cached, SlotResult) else None
            if restored is not None and self._cache is not None:
                self._cache[(slot.key, content_hash)] = restored  # 回填进程内，避免同任务重复查询
            return restored
        return None

    async def _cache_store(self, slot: Slot, chunks: Sequence[TextBlock], result: SlotResult) -> None:
        """两级缓存写入：只写「明确结果」（OK / 需人工核对），失败不缓存（否则固化失败）。"""
        if result.state not in (status.STATUS_OK, status.STATUS_NEEDS_VERIFY):
            return
        content_hash = self._content_hash(chunks)
        if self._cache is not None:
            self._cache[(slot.key, content_hash)] = result
        if self._persist_cache is not None:
            try:
                await self._persist_cache.put(self._persist_cache.key(slot.key, content_hash), result)
            except Exception:  # noqa: BLE001 - 缓存是旁路，异常不影响提取
                logger.exception("提取结果写入持久缓存失败（忽略）")

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

    def _finalize_slot(
        self, slot: Slot, out: SlotOut | None, pool: Sequence[dict[str, Any]] | None = None
    ) -> SlotResult:
        """校验单个填充项输出。

        依据核对分级处理：
        - 精确命中 → 正常落地；
        - 仅模糊命中 → 值照常写入，但标 needs_verify 提示人工核对（大概率只是排版/OCR 差异）；
        - 引用文本完全无法核对 → 先按模型自报的资料编号（refs）在被引片段内复核取值，
          能定位则保留取值并标 needs_verify；再退到全语料精确命中；都不行才占位待补充
          （AI 给出的值与候选始终保留，不再丢弃）。
        """
        if out is None:
            return SlotResult(
                key=slot.key,
                text=status.pending("AI 未返回该填充项结果"),
                state=status.STATUS_FAILED,
                gap_reason=gap.GAP_MODEL_FAILED,
            )
        value = str(out.value or "").strip()
        if not out.found or not value:
            return SlotResult(
                key=slot.key,
                text=status.pending("资料中未找到依据"),
                state=status.STATUS_PENDING,
                gap_reason=gap.GAP_NOT_FOUND,
            )
        exact, fuzzy = self._split_evidence(out.evidence)
        if not exact and not fuzzy:
            # 引用文本没核对上，不等于引用本身无据：先按模型自报的资料编号（refs）复核——
            # 编号指向的片段里有完整取值或全部数字，说明确有依据，只是引用抄写不可靠
            if self._value_in_refs(pool, out.refs, value):
                self.stats.refs_rescued += 1
                return SlotResult(
                    key=slot.key,
                    text=value,
                    state=status.STATUS_NEEDS_VERIFY,
                    reason="引用文本未能核对，但取值可在所引资料中定位，请人工确认",
                    evidence=list(out.evidence),
                    confidence=out.confidence,
                    gap_reason=gap.GAP_EVIDENCE_REJECTED,
                )
            if self._value_locatable(value):
                # 引用没核对上，但取值本身能在原文中定位：内容大概率真实、只是引用不可靠
                # （模型改写/漏抄了引用片段）。保留取值并降级为需人工核对，比整条打回
                # 「待补充」少丢信息；注意这不是「已验证」，仍要人工确认。
                return SlotResult(
                    key=slot.key,
                    text=value,
                    state=status.STATUS_NEEDS_VERIFY,
                    reason="引用未能核对，但取值可在原文中定位，请人工确认",
                    evidence=list(out.evidence),
                    confidence=out.confidence,
                    gap_reason=gap.GAP_EVIDENCE_REJECTED,
                )
            if slot.draft_allowed:
                return SlotResult(
                    key=slot.key,
                    text=status.with_draft_prefix(value),
                    state=status.STATUS_DRAFT,
                    reason="引用未能核对，需人工确认",
                    candidates=[str(c) for c in out.candidates],
                    confidence=out.confidence,
                    gap_reason=gap.GAP_EVIDENCE_REJECTED,
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
                gap_reason=gap.GAP_EVIDENCE_REJECTED,
            )
        if fuzzy and not exact:
            return SlotResult(
                key=slot.key,
                text=value,
                state=status.STATUS_NEEDS_VERIFY,
                reason="引用经模糊匹配核对（存在排版/识别差异），请人工确认",
                evidence=fuzzy,
                confidence=out.confidence,
                gap_reason=gap.GAP_FUZZY_EVIDENCE,
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
                gap_reason=gap.GAP_CONFLICT,
            )
        format_error = _format_error(slot, value)
        if format_error:
            return SlotResult(
                key=slot.key,
                text=status.pending(format_error),
                state=status.STATUS_PENDING,
                gap_reason=gap.GAP_FORMAT_ERROR,
            )
        return self._grade_confidence(
            self._check_requirement(
                slot,
                SlotResult(key=slot.key, text=value, state=status.STATUS_OK, evidence=exact, confidence=out.confidence),
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
            result.gap_reason = gap.GAP_LOW_CONFIDENCE
            return result
        if result.confidence < self._confidence_high:
            self.stats.low_confidence += 1
        return result

    def _check_requirement(self, slot: Slot, result: SlotResult) -> SlotResult:
        """按需求描述校验取值（template_structure v2）。

        需求描述是模板分析给出的「期望」而非硬约束：不符时值照常写入正文，
        只降级为需人工核对并写明不符项，避免把有效内容整条丢掉。
        """
        mismatches = _requirement_mismatch(slot, result.text)
        if not mismatches:
            return result
        result.state = status.STATUS_NEEDS_VERIFY
        result.reason = "；".join(mismatches) + "，请人工确认"
        result.gap_reason = gap.GAP_REQUIREMENT
        self.stats.requirement_mismatches += 1
        return result

    def _corpus_of(self, file_id: str) -> str:
        """取某份资料的归一化语料；file_id 未知时退回全部语料拼接。

        知识库命中片段不在 ``_by_file``（它们不参与本地检索），必须单独查 ``_kb_raw``，
        否则模型引用知识库内容会被判成无依据。
        """
        haystack = self._by_file.get(file_id)
        if haystack is None and file_id.startswith(KB_FILE_PREFIX):
            raw = self._kb_raw.get(file_id)
            if raw:
                return _normalize_text("".join(raw))
        if haystack is None:
            haystack = "".join(self._by_file.values())
            if self._kb_raw:
                haystack += "".join(_normalize_text("".join(parts)) for parts in self._kb_raw.values())
        return haystack

    def _all_corpus(self) -> str:
        """全部语料的归一化拼接（不缓存：``_kb_raw`` 随召回增量，缓存会漏掉新片段）。

        只在引用核对全失败、需要做取值定位兜底时调用，频率低。
        """
        parts = list(self._by_file.values())
        parts.extend(_normalize_text("".join(raw)) for raw in self._kb_raw.values())
        return "".join(parts)

    def _value_locatable(self, value: str) -> bool:
        """取值本身能否在语料中定位（不依赖模型给出的引用）。

        引用没核对上，不等于值不真实——模型抄引用时可能改写了措辞或漏抄了片段。
        这里做一次保守兜底：归一化后的**完整取值**必须是语料的精确子串才算「可定位」，
        长度 <4 不判（避免「是」「无」这类短词任意命中），也不接受「只有数字命中」的
        弱证据（一个裸数字出现在语料里，不代表它属于这个填充项）。
        命中只是把结果降级为 needs_verify 交人工，不会直接判为已验证。
        """
        needle = _normalize_text(value)
        if len(needle) < 4:
            return False
        return needle in self._all_corpus()

    def _value_in_refs(self, pool: Sequence[dict[str, Any]] | None, refs: Sequence[Any], value: str) -> bool:
        """按模型自报的资料编号复核取值（不依赖它抄写的引用文本）。

        编号无效（越界/非数字）直接判否；编号有效时要求「完整取值命中」或「取值里所有
        长度 ≥2 的数字都能在被引资料中找到」。限定在被引片段内比全语料命中可信得多
        ——模型明确指向了它依据的资料，数字全对基本可排除凭空生成。
        命中只是把结果降级为 needs_verify 交人工，不会判为已验证。
        """
        if not pool or not refs:
            return False
        parts: list[str] = []
        for ref in refs:
            try:
                pos = int(ref) - 1
            except (TypeError, ValueError):
                continue
            if 0 <= pos < len(pool):
                parts.append(str(pool[pos].get("text") or ""))
        haystack = _normalize_text("".join(parts))
        if not haystack:
            return False
        needle = _normalize_text(value)
        if len(needle) >= 4 and needle in haystack:
            return True
        numbers = [token for token in _NUMBER_RE.findall(value) if len(token) >= 2]
        if not numbers:
            return False
        return all(_normalize_text(token) in haystack for token in numbers)

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
            pos = haystack.find(needle[mid_start:][:_FUZZY_ANCHOR_LEN])
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

    def _table_row_verified(
        self, item: Mapping[str, Any], record: Mapping[str, str], pool: Sequence[dict[str, Any]] | None
    ) -> bool:
        """表格行是否有可核对的依据。

        两级：带引用（evidence）的走字符串回检；只带资料编号（refs）的按「所引片段内能否
        定位行值」复核（拼接行内各列，完整命中或全部数字命中即算）。都没有则判为未核对——
        表格是「模型最容易顺手补全」的位置，行数据必须能追回到原文才算可信。
        """
        for raw in item.get("evidence") or []:
            model = _to_evidence(raw)
            if model is not None and self._verify_quote(model)[0]:
                return True
        refs = list(item.get("refs") or [])
        if refs:
            joined = " ".join(value for value in record.values() if value)
            if joined and self._value_in_refs(pool, refs, joined):
                return True
        return False

    async def _extract_table(self, slot: Slot) -> SlotResult:
        """表格槽位：逐行抽取，计算列与序号交给程序。"""
        if slot.manual_only:
            return SlotResult(key=slot.key, state=status.STATUS_MANUAL, reason="需人工填写", gap_reason=gap.GAP_MANUAL)
        chunks, pool, _wide = await self._candidates(slot)
        if not chunks:
            return SlotResult(
                key=slot.key,
                state=status.STATUS_PENDING,
                reason="资料中未找到相关表格数据",
                gap_reason=gap.GAP_NO_MATERIAL,
            )
        payload = _slot_payload(slot)
        writable = [c for c in payload["columns"] if c.get("writable")]
        if not writable:
            return SlotResult(
                key=slot.key, state=status.STATUS_MANUAL, reason="该表所有列均为程序计算", gap_reason=gap.GAP_MANUAL
            )
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
        unverified_rows = 0
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
            if not record or not any(record.values()):
                continue
            if not self._table_row_verified(item, record, pool):
                unverified_rows += 1
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
                key=slot.key,
                state=status.STATUS_PENDING,
                reason="资料中未找到表格数据",
                evidence=evidence,
                gap_reason=gap.GAP_NO_MATERIAL,
            )
        # 有未核对行时不丢数据，但整表降级为「需人工核对」——表格行是最容易被顺手补全的位置，
        # 可信度不足必须让人看见，而不是混在 OK 里
        if unverified_rows:
            self.stats.table_rows_unverified += unverified_rows
            reason = f"{unverified_rows}/{len(rows)} 行引用未能核对，请人工确认"
            if truncated:
                return SlotResult(
                    key=slot.key,
                    rows=rows,
                    state=status.STATUS_OVERFLOW,
                    reason=f"行数超过模板原件可承载上限 {limit}，已截断；{reason}",
                    evidence=evidence,
                    gap_reason=gap.GAP_EVIDENCE_REJECTED,
                )
            return SlotResult(
                key=slot.key,
                rows=rows,
                state=status.STATUS_NEEDS_VERIFY,
                reason=reason,
                evidence=evidence,
                # 归因「依据未核对上」：缺口闭环会对它换口径重试（只接受更好的结果，
                # 例如重试后抽到带可核对引用的行）；定向补问不会碰它（probe 跳过表格）
                gap_reason=gap.GAP_EVIDENCE_REJECTED,
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
    """把槽位定义转成 prompt 可用的字典（含需求描述）。"""
    sequence_key = slot.table.sequence_column if slot.table else None
    return {
        "key": slot.key,
        "label": slot.label,
        "expects": slot.expects,
        "max_chars": slot.max_chars,
        "required": slot.required,
        "draft_allowed": slot.draft_allowed,
        "query_hint": slot.query_hint,
        "section": slot.section,
        # 需求描述（template_structure v2）：让模型知道该槽位期望的量纲/枚举/基数/来源
        "unit": slot.unit,
        "enum_values": list(slot.enum_values),
        "cardinality": slot.cardinality,
        "source_scope": slot.source_scope,
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


def _requirement_mismatch(slot: Slot, value: str) -> list[str]:
    """按需求描述（量纲/允许取值）核对取值，返回不符项描述。

    量纲与枚举都是「必须出现」的下限约束（NFKC + 去空白后包含即算命中）：资料里的
    写法很杂（``mg/ml`` / ``毫克/毫升`` / ``片剂（规格 0.5g）``），过严的正则会误伤正确输出。
    """
    haystack = _normalize_text(value)
    mismatches: list[str] = []
    if slot.unit and _normalize_text(slot.unit) not in haystack:
        mismatches.append(f"量纲不符（要求 {slot.unit}）")
    options = [item for item in slot.enum_values if item.strip()]
    if options and not any(_normalize_text(item) in haystack for item in options):
        mismatches.append(f"取值不在允许范围（{'、'.join(options[:5])}）")
    return mismatches
