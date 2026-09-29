"""知识库覆盖预检（A2）：生成之前先算清楚「这些填充项，库里到底有没有料」。

设计要点
--------
1. **只做归类，不做抽取**：预检不调 LLM，只回答每个填充项的取值来源（项目知识库）
   里能不能找到对得上的说法，输出三档：可填 / 部分可填 / 无资料。
2. **离线优先**：优先在本地索引（``rd_kb_chunks`` 切片 + ``rd_kb_facts`` 事实）里做词面匹配，
   快且不压 RAGFlow；索引为空（知识库刚建、还没跑过任务）时才退化为实时多查询检索兜底。
3. **口径可解释**：槽位的主口径是「槽位名 + 检索提示」，同义词（``search_terms``）与表格列名
   算别名。**主口径命中 → 可填；只有别名命中 → 部分可填；一条都没有 → 无资料**。
   宁可保守（把「部分可填」留给人看），也不虚报覆盖。
4. **结果可回流**：``as_job_stats()`` 会并进 ``job.stats``，供完成后页与指标看板复用；
   预检接口同一个函数即可返回给前端确认弹窗。
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec
from app.modules.research.knowledge_base import facts as kb_facts
from app.modules.research.knowledge_base.models import RdKbChunk, RdKnowledgeBase

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 三档覆盖状态（+ 一档「不适用」）
# ---------------------------------------------------------------------------
COVERAGE_FILLABLE = "fillable"  # 可填：库里直接能对上槽位口径
COVERAGE_PARTIAL = "partial"  # 部分可填：只找到别名/近似说法，需要人工确认
COVERAGE_NO_MATERIAL = "no_material"  # 无资料：库里找不到任何相关说法
COVERAGE_SKIPPED = "skipped"  # 不适用：元数据槽位、人工槽位、无检索词、图片槽位

COVERAGE_LABELS: dict[str, str] = {
    COVERAGE_FILLABLE: "可填",
    COVERAGE_PARTIAL: "部分可填",
    COVERAGE_NO_MATERIAL: "无资料",
    COVERAGE_SKIPPED: "不适用",
}

# 匹配用了哪一层资料
SOURCE_INDEX = "index"  # 本地索引（切片 + 事实），离线匹配
SOURCE_LIVE = "live"  # 实时检索兜底（多查询打 RAGFlow）
SOURCE_NONE = "none"  # 没有可用资料源

SOURCE_LABELS: dict[str, str] = {
    SOURCE_INDEX: "知识库索引",
    SOURCE_LIVE: "实时检索",
    SOURCE_NONE: "无可用资料",
}

# ---------------------------------------------------------------------------
# 匹配参数
# ---------------------------------------------------------------------------
_MIN_TERM_CHARS = 2  # 单字关键词噪声太大，不参与匹配
_TEXT_LIMIT_CHARS = 1500  # 单条索引文本参与匹配的截断长度（尾部基本是重复内容）
_PARTIAL_WEIGHT = 0.5  # 「部分可填」在加权覆盖率里的权重
_MISSING_PREVIEW = 8  # 落库时保留的无资料槽位名数量上限

_WS_RE = re.compile(r"\s+")


def _normalize(text: str) -> str:
    """归一化：NFKC + 去所有空白 + 小写（与解析层口径一致，避免全半角/大小写假阴性）。"""
    return _WS_RE.sub("", unicodedata.normalize("NFKC", text or "")).lower()


def _dedupe(terms: list[str]) -> list[str]:
    """保留顺序去重，丢掉空白与过短词。"""
    seen: set[str] = set()
    result: list[str] = []
    for raw in terms:
        term = (raw or "").strip()
        if not term or len(_normalize(term)) < _MIN_TERM_CHARS or term in seen:
            continue
        seen.add(term)
        result.append(term)
    return result


def probe_terms(slot: Slot) -> tuple[list[str], list[str]]:
    """槽位的检索口径：返回 ``(主口径, 别名)``。

    主口径 = 槽位名 + 检索提示（生成时 prompt 就是这么告诉模型的）；
    别名 = ``search_terms`` 同义词 + 表格列名（表格槽位一行多列，列名才是真正的填充位置）。
    """
    primary = _dedupe([slot.label, slot.query_hint])
    alternates = _dedupe([*slot.search_terms, *(column.label for column in slot.columns)])
    primary_set = set(primary)
    return primary, [term for term in alternates if term not in primary_set]


def is_checkable(slot: Slot) -> bool:
    """该槽位是否需要覆盖预检：元数据 / 人工槽位不查库，图片槽位没有文字可不查。"""
    if slot.from_meta or slot.manual_only:
        return False
    return slot.kind != "image"


def classify(*, primary_hits: int, alternate_hits: int, material_hits: int) -> str:
    """按命中的口径层次归类（见模块 docstring 第 3 条）。"""
    if primary_hits > 0:
        return COVERAGE_FILLABLE
    if alternate_hits > 0 or material_hits > 0:
        return COVERAGE_PARTIAL
    return COVERAGE_NO_MATERIAL


@dataclass(slots=True)
class SlotCoverage:
    """单个槽位的覆盖预检结果。"""

    key: str
    label: str
    kind: str
    required: bool
    status: str = COVERAGE_NO_MATERIAL
    matched_terms: int = 0  # 命中的口径词数量（主口径 + 别名）
    material_hits: int = 0  # 命中的索引文本条数

    @property
    def status_label(self) -> str:
        return COVERAGE_LABELS.get(self.status, self.status)

    def as_payload(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "kind": self.kind,
            "required": self.required,
            "status": self.status,
            "status_label": self.status_label,
            "matched_terms": self.matched_terms,
        }


@dataclass(slots=True)
class KbCoverage:
    """一次覆盖预检的整体结果。"""

    entries: list[SlotCoverage] = field(default_factory=list)
    source: str = SOURCE_NONE
    kb_id: str = ""
    kb_name: str = ""
    documents: int = 0  # 知识库文件数（快照值，用于说明「为什么没料」）
    chunks: int = 0  # 参与匹配的切片数
    facts: int = 0  # 参与匹配的结构化事实数
    truncated: bool = False  # 索引载入是否被上限截断
    warnings: list[str] = field(default_factory=list)

    # -- 统计 -------------------------------------------------------------
    @property
    def total(self) -> int:
        return len(self.entries)

    @property
    def checked(self) -> int:
        return sum(1 for entry in self.entries if entry.status != COVERAGE_SKIPPED)

    @property
    def fillable(self) -> int:
        return sum(1 for entry in self.entries if entry.status == COVERAGE_FILLABLE)

    @property
    def partial(self) -> int:
        return sum(1 for entry in self.entries if entry.status == COVERAGE_PARTIAL)

    @property
    def missing(self) -> int:
        return sum(1 for entry in self.entries if entry.status == COVERAGE_NO_MATERIAL)

    @property
    def skipped(self) -> int:
        return sum(1 for entry in self.entries if entry.status == COVERAGE_SKIPPED)

    @property
    def fillable_ratio(self) -> float:
        """严格覆盖率：可填 / 需检索的槽位数。"""
        checked = self.checked
        return round(self.fillable / checked, 3) if checked else 0.0

    @property
    def weighted_ratio(self) -> float:
        """加权覆盖率：可填记 1 分、部分可填记 0.5 分（门禁判断用这个更合理）。"""
        checked = self.checked
        if not checked:
            return 0.0
        return round((self.fillable + _PARTIAL_WEIGHT * self.partial) / checked, 3)

    @property
    def missing_labels(self) -> list[str]:
        return [entry.label or entry.key for entry in self.entries if entry.status == COVERAGE_NO_MATERIAL]

    def as_job_stats(self) -> dict[str, Any]:
        """并进 ``job.stats`` 的扁平字段（完成页/看板直接读，不用再爬嵌套结构）。"""
        return {
            "kb_coverage_source": self.source,
            "kb_coverage_checked": self.checked,
            "kb_coverage_fillable": self.fillable,
            "kb_coverage_partial": self.partial,
            "kb_coverage_missing": self.missing,
            "kb_coverage_ratio": self.weighted_ratio,
            "kb_coverage_missing_labels": self.missing_labels[:_MISSING_PREVIEW],
        }

    def as_payload(self) -> dict[str, Any]:
        """接口返回体（``data`` 部分）。"""
        return {
            "source": self.source,
            "source_label": SOURCE_LABELS.get(self.source, self.source),
            "kb_id": self.kb_id,
            "kb_name": self.kb_name,
            "documents": self.documents,
            "chunks": self.chunks,
            "facts": self.facts,
            "truncated": self.truncated,
            "warnings": list(self.warnings),
            "total": self.total,
            "checked": self.checked,
            "fillable": self.fillable,
            "partial": self.partial,
            "missing": self.missing,
            "skipped": self.skipped,
            "fillable_ratio": self.fillable_ratio,
            "weighted_ratio": self.weighted_ratio,
            "slots": [entry.as_payload() for entry in self.entries],
        }


@dataclass(slots=True)
class IndexedMaterial:
    """本地索引载入结果（已归一化，直接参与匹配）。"""

    texts: list[str] = field(default_factory=list)
    chunks: int = 0
    facts: int = 0
    truncated: bool = False


async def load_index_texts(session: AsyncSession, kb_id: Any, *, max_chunks: int) -> IndexedMaterial:
    """载入本地索引文本：结构化事实（优先，密度高）+ 原始切片（兜底，覆盖事实漏抽的内容）。"""
    material = IndexedMaterial()
    if max_chunks <= 0:
        material.truncated = True
        return material

    fact_rows = await kb_facts.load_facts(session, kb_id, limit=max_chunks)
    for fact in fact_rows:
        parts = [fact.subject, fact.predicate, fact.value, fact.unit, fact.quote]
        text = " ".join(part for part in parts if part)
        if text:
            material.texts.append(_normalize(text)[:_TEXT_LIMIT_CHARS])
            material.facts += 1

    remaining = max_chunks - material.facts
    if remaining <= 0:
        material.truncated = True
    else:
        stmt = (
            select(RdKbChunk.content)
            .where(RdKbChunk.kb_id == kb_id, RdKbChunk.is_deleted.is_(False))
            .order_by(RdKbChunk.created_at)
            .limit(remaining)
        )
        rows = (await session.execute(stmt)).scalars().all()
        for content in rows:
            text = _normalize(content or "")[:_TEXT_LIMIT_CHARS]
            if text:
                material.texts.append(text)
                material.chunks += 1
    return material


@dataclass(slots=True)
class _Probe:
    """一次槽位探测的可变中间状态（离线/实时两条路径共用匹配逻辑）。"""

    entry: SlotCoverage
    primary: list[str]
    alternates: list[str]
    primary_hits: int = 0
    alternate_hits: int = 0
    material_hits: int = 0

    def finish(self) -> None:
        self.entry.status = classify(
            primary_hits=self.primary_hits,
            alternate_hits=self.alternate_hits,
            material_hits=self.material_hits,
        )
        self.entry.matched_terms = self.primary_hits + self.alternate_hits
        self.entry.material_hits = self.material_hits


def _match_texts(probe: _Probe, texts: list[str]) -> None:
    """在（已归一化的）文本集合里找口径词：主口径一命中就提前收工。"""
    primary = [_normalize(term) for term in probe.primary]
    alternates = [_normalize(term) for term in probe.alternates]
    for text in texts:
        hits = sum(1 for term in primary if term in text)
        if hits:
            probe.primary_hits = max(probe.primary_hits, hits)
            probe.material_hits += 1
            return
        hits = sum(1 for term in alternates if term in text)
        if hits:
            probe.alternate_hits = max(probe.alternate_hits, hits)
            probe.material_hits += 1


async def _match_live(probes: list[_Probe], retriever: Any, *, timeout_seconds: float) -> bool:
    """实时检索兜底：一个槽位一次查询（多查询），整体加超时；返回是否超时。"""

    async def _one(probe: _Probe) -> None:
        try:
            blocks = await retriever.retrieve([*probe.primary, *probe.alternates])
        except Exception:  # noqa: BLE001 - 单个槽位失败不影响整体预检
            logger.warning("覆盖预检实时检索失败，槽位按无资料处理", extra={"slot": probe.entry.key}, exc_info=True)
            return
        _match_texts(probe, [_normalize(block.text)[:_TEXT_LIMIT_CHARS] for block in blocks if block.text])

    try:
        await asyncio.wait_for(asyncio.gather(*(_one(probe) for probe in probes)), timeout=timeout_seconds)
    except TimeoutError:
        return True
    return False


def _build_probes(spec: TemplateSpec, coverage: KbCoverage) -> list[_Probe]:
    """把模板槽位拆成「需预检」与「不适用」两组，并同步写入 ``coverage.entries``。"""
    probes: list[_Probe] = []
    for slot in spec.slots:
        primary, alternates = probe_terms(slot)
        entry = SlotCoverage(
            key=slot.key,
            label=slot.label,
            kind=slot.kind,
            required=slot.required,
            status=COVERAGE_SKIPPED,
        )
        coverage.entries.append(entry)
        if not is_checkable(slot) or not (primary or alternates):
            continue
        entry.status = COVERAGE_NO_MATERIAL
        probes.append(_Probe(entry=entry, primary=primary, alternates=alternates))
    return probes


async def evaluate_coverage(
    session: AsyncSession,
    spec: TemplateSpec,
    *,
    kb: RdKnowledgeBase | None,
    live_retriever: Any = None,
    max_chunks: int = 3000,
    max_slots: int = 60,
    live_fallback: bool = True,
    live_timeout_seconds: float = 45.0,
    documents: int = 0,
) -> KbCoverage:
    """对一份模板做知识库覆盖预检。

    参数
    ----
    kb: 目标项目知识库；为 ``None``（未挂库）时全部按「无资料」返回并给出告警。
    live_retriever: 实时检索器；``None`` 或不可用时不做实时兜底。
    live_fallback: 本地索引为空时是否退化到实时检索。流水线内已建过索引，应传 ``False``。
    """
    started = time.monotonic()
    coverage = KbCoverage(documents=documents)
    if kb is not None:
        coverage.kb_id = str(kb.id)
        coverage.kb_name = kb.name or ""

    probes = _build_probes(spec, coverage)
    if not probes:
        return coverage

    if kb is None or kb.is_deleted or not kb.ragflow_dataset_id:
        coverage.source = SOURCE_NONE
        coverage.warnings.append("项目未挂可用知识库，AI 只能依赖登记数据与补充说明")
        return coverage

    material = await load_index_texts(session, kb.id, max_chunks=max_chunks)
    coverage.chunks = material.chunks
    coverage.facts = material.facts
    coverage.truncated = material.truncated

    if material.texts:
        coverage.source = SOURCE_INDEX
        for probe in probes:
            _match_texts(probe, material.texts)
            probe.finish()
    elif live_fallback and live_retriever is not None:
        coverage.source = SOURCE_LIVE
        targets = probes[:max_slots]
        if len(probes) > max_slots:
            coverage.warnings.append(f"槽位超过实时检索上限（{max_slots}），其余槽位未预检")
        timed_out = await _match_live(targets, live_retriever, timeout_seconds=live_timeout_seconds)
        if timed_out:
            coverage.warnings.append("实时检索超时，覆盖结果只包含已完成部分")
        for probe in targets:
            probe.finish()
    else:
        coverage.source = SOURCE_NONE
        coverage.warnings.append("知识库尚未建立索引，请先在知识库页运行一次预检或生成任务")

    logger.info(
        "知识库覆盖预检完成",
        extra={
            "kb_id": coverage.kb_id,
            "template": spec.code,
            "source": coverage.source,
            "checked": coverage.checked,
            "fillable": coverage.fillable,
            "partial": coverage.partial,
            "missing": coverage.missing,
            "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
        },
    )
    return coverage
