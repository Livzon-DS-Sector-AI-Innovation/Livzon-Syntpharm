"""Agent 可调用的工具集：读母本、查知识库、把内容写进模板、收尾整理参考资料。

工具是「模型能看见的世界边界」。所有写入都只落 ``RdReportGenSlot`` 写入记录，不直接
改 docx：出稿时由 ``render.render_document`` 一次性回放，这样

- 重渲（按记录重出 docx）天然可用；
- 插入新段落后母本下标漂移不会影响后续写入；
- 写保护只需在工具层校验母本属性，与渲染解耦，负例好测。

每个工具都返回 ``ToolOutcome``（一句话摘要给步骤流 + 结构化结果给模型看），并且
**不抛异常给上层**：工具失败本身是执行过程的一部分，记录后让模型自己换位或改查。
"""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, cast

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.knowledge_base.models import RdKbChunk, RdKbFact, RdKnowledgeBase
from app.modules.research.knowledge_base.ragflow import RagflowClient
from app.modules.research.models import (
    RdExperimentLog,
    RdProject,
    RdReportGenJob,
    RdReportGenSlot,
    RdStageRecord,
)
from app.modules.research.report_gen.cell_semantics import validate_cell_value
from app.modules.research.report_gen.outline import (
    MAX_OUTLINE_TEXT,
    TemplateOutline,
    WritablePosition,
)
from app.modules.research.report_gen.references import build_reference_groups, format_reference_entries
from app.modules.research.report_gen.render import (
    KIND_APPEND_PARAGRAPH,
    KIND_APPEND_TABLE_ROWS,
    KIND_PARAGRAPH,
    KIND_REFERENCES,
    KIND_TABLE_CELL,
)

logger = logging.getLogger(__name__)

# 交给模型的输出上限：既控制 context 长度，也避免步骤表被长文本撑爆
_MAX_TOOL_TEXT = 1500
# 一次检索最多几个查询词：再多就是让模型把整段正文当检索词，命中率反而下降
_DEFAULT_QUERY_LIMIT = 5
# 单个段落的正文上限：模板里的空位不是写长篇的地方
_MAX_WRITE_CHARS = 4000


@dataclass(slots=True)
class ToolOutcome:
    ok: bool
    summary: str
    payload: dict[str, Any] = field(default_factory=dict)


def _cut(text: Any, limit: int = _MAX_TOOL_TEXT) -> str:
    value = "" if text is None else str(text)
    value = " ".join(value.split())
    return value if len(value) <= limit else value[:limit] + "…"


def _jsonable(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    return value


def _as_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


class ReportGenRuntime:
    """一次任务内的工具执行上下文（session、任务行、母本全貌、写入记录）。"""

    def __init__(
        self,
        session: AsyncSession,
        job: RdReportGenJob,
        project: RdProject,
        outline: TemplateOutline,
        slot_rows: dict[str, RdReportGenSlot],
        config: Any,
        *,
        report_title: str = "",
        instruction: str = "",
    ) -> None:
        self.session = session
        self.job = job
        self.project = project
        self.report_title = report_title
        self.outline = outline
        self.positions: dict[str, WritablePosition] = outline.by_key()
        self.slot_rows = slot_rows
        self.config = config
        # 模板级填写要求：由 template_structure.instruction 下发，属于软约束
        self.instruction = instruction
        # 检索来源登记：source_id → 来源名与原文证据，写入时按 id 引用，
        # 参考资料直接从同一份登记生成，保证「正文与引用一一对应」
        self.sources: dict[str, dict[str, str]] = {}
        self._source_index: dict[tuple[str, str], str] = {}
        self._source_seq = 0
        self._append_seq = 0
        self.rejected = 0
        # 出稿前语义复核命中的位置：只标记待核对，不改内容
        self.semantic_mismatches: list[dict[str, Any]] = []
        self.finalized = False
        self.final_summary = ""
        self.kb: RdKnowledgeBase | None = None
        self._kb_loaded = False

    # ------------------------------------------------------------------
    # 工具：读母本
    # ------------------------------------------------------------------
    def _human_locked(self, key: str) -> bool:
        """人工确认过的位置：下一次生成沿用人工值，模型不得再写。"""
        row = self.slot_rows.get(key)
        if row is None:
            return False
        anchor = row.anchor if isinstance(row.anchor, dict) else {}
        return anchor.get("human_locked") is True

    def _next_append_key(self, prefix: str) -> tuple[int, str]:
        """分配追加项 key：跳过已存在的人工确认行，避免把人工内容覆盖掉。"""
        while True:
            self._append_seq += 1
            key = f"{prefix}{self._append_seq}"
            if key not in self.slot_rows:
                return self._append_seq, key

    def read_template_outline(self, arguments: dict[str, Any]) -> ToolOutcome:
        """分页读可写位置；也支持按表格整表读取（表格里逐格看更直观）。"""
        only_writable = arguments.get("only_writable")
        only_writable = True if only_writable is None else bool(only_writable)
        table_index = _as_int(arguments.get("table_index"))

        base = self.outline.writable if only_writable else self.outline.positions
        pool = [item for item in base if not self._human_locked(item.key)]
        locked_total = sum(1 for item in self.outline.writable if self._human_locked(item.key))
        if table_index is not None:
            pool = [item for item in pool if item.kind == KIND_TABLE_CELL and item.index == table_index]
            offset, limit = 0, max(len(pool), 1)
        else:
            offset = max(_as_int(arguments.get("offset")) or 0, 0)
            limit = min(max(_as_int(arguments.get("limit")) or 40, 1), 120)

        page = pool[offset : offset + limit]
        next_offset = offset + len(page)
        payload: dict[str, Any] = {
            "writable_total": max(self.outline.writable_total - locked_total, 0),
            "human_locked_total": locked_total,
            "position_total": len(self.outline.positions),
            "offset": offset,
            "returned": len(page),
            "only_writable": only_writable,
            "items": [item.brief() for item in page],
        }
        if table_index is not None:
            payload["table_index"] = table_index
        if next_offset < len(pool):
            payload["next_offset"] = next_offset
        if offset == 0 and table_index is None:
            payload["sections"] = self.outline.section_brief()
            payload["tables"] = self.outline.table_count
            payload["note"] = (
                "key 就是写入时用的位置标识：p{n} 段落、t{表}r{行}c{列} 单元格。"
                "context 是上一段/行标题文字；表格还有一个 column_hint（列路径，如「自研成本 › 研发投入」），"
                "两者一起说明该位置该写什么。expect 是这一格期望的内容类型"
                "（number 数值 / cas CAS号 / formula 分子式 / opinion 评审意见 / text 文本），"
                "写入前会按它校验。"
                "append=true 的是「标签：」段：text 只给冒号后的值，标签由系统保留。"
                "注意：不要按顺序往一排空格里填值；对不上 column_hint 含义的格子留空，"
                "由人工补写。"
            )
        return ToolOutcome(
            ok=True,
            summary=(
                f"可写位置 {max(self.outline.writable_total - locked_total, 0)} 个"
                f"（人工已确认 {locked_total} 处不需重写），本次返回 {offset + 1}-{next_offset}"
                if locked_total
                else f"可写位置 {self.outline.writable_total} 个，本次返回 {offset + 1}-{next_offset}"
            ),
            payload=payload,
        )

    # ------------------------------------------------------------------
    # 工具：项目上下文
    # ------------------------------------------------------------------
    async def read_project_context(self, arguments: dict[str, Any]) -> ToolOutcome:
        section = str(arguments.get("section") or "all")
        payload: dict[str, Any] = {"project": self._project_basic()}
        if section in ("all", "stages"):
            payload["stage_records"] = await self._stage_records()
        if section in ("all", "experiments"):
            payload["experiment_logs"] = await self._experiment_logs()
        if section == "all":
            payload["report_input"] = {
                "title": self.report_title,
                "doc_code": self.job.doc_code,
                "drug_name": self.job.drug_name,
                "supplement": _cut(self.job.supplement_text, 1000),
            }
        stages = len(payload.get("stage_records") or [])
        experiments = len(payload.get("experiment_logs") or [])
        return ToolOutcome(
            ok=True,
            summary=f"项目 {self.project.name}｜阶段记录 {stages} 条｜实验记录 {experiments} 条",
            payload=_jsonable(payload),
        )

    def _project_basic(self) -> dict[str, Any]:
        project = self.project
        return {
            "name": project.name,
            "api_name": project.api_name,
            "cas_number": project.cas_number,
            "molecular_formula": project.molecular_formula,
            "molecular_weight": project.molecular_weight,
            "indication": _cut(project.indication, 300),
            "project_type": project.project_type,
            "current_stage": project.current_stage,
            "status": project.status,
            "start_date": project.start_date,
            "target_filing_date": project.target_filing_date,
            "overall_progress": project.overall_progress,
            "notes": _cut(project.notes, 500),
        }

    async def _stage_records(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(RdStageRecord)
            .where(RdStageRecord.project_id == self.project.id, RdStageRecord.is_deleted.is_(False))
            .order_by(RdStageRecord.created_at.desc())
            .limit(8)
        )
        return [
            {
                "stage": row.stage,
                "status": row.status,
                "version": row.version,
                "input_summary": _jsonable(row.input_summary),
                "output_summary": _jsonable(row.output_summary),
                "gate_review_status": row.gate_review_status,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
            }
            for row in result.scalars().all()
        ]

    async def _experiment_logs(self) -> list[dict[str, Any]]:
        result = await self.session.execute(
            select(RdExperimentLog)
            .where(RdExperimentLog.project_id == self.project.id, RdExperimentLog.is_deleted.is_(False))
            .order_by(RdExperimentLog.experiment_date.desc().nullslast())
            .limit(8)
        )
        return [
            {
                "title": row.title,
                "experiment_type": row.experiment_type,
                "experiment_date": row.experiment_date,
                "status": row.status,
                "objective": _cut(row.objective, 300),
                "conclusion": _cut(row.conclusion, 600),
                "results": _cut(row.results, 600),
                "issues": _cut(row.issues, 300),
            }
            for row in result.scalars().all()
        ]

    # ------------------------------------------------------------------
    # 工具：知识库
    # ------------------------------------------------------------------
    async def search_knowledge_base(self, arguments: dict[str, Any]) -> ToolOutcome:
        raw_queries = arguments.get("queries")
        if isinstance(raw_queries, list) and raw_queries:
            queries = [str(item).strip() for item in raw_queries if str(item or "").strip()]
        else:
            queries = [str(arguments.get("query") or "").strip()]
        queries = [item for item in queries if item]
        if not queries:
            return ToolOutcome(ok=False, summary="query 不能为空", payload={"error": "query 不能为空"})

        limit = min(max(_as_int(self.config.search_query_limit) or _DEFAULT_QUERY_LIMIT, 1), 8)
        if len(queries) > limit:
            queries = queries[:limit]
        top_k = min(max(_as_int(arguments.get("top_k")) or self.config.kb_top_k, 1), 12)

        kb = await self._resolve_kb()
        if kb is None:
            return ToolOutcome(
                ok=False,
                summary="这个项目还没有知识库，没查到资料",
                payload={"error": "这个项目还没有知识库", "items": []},
            )

        items: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for query in queries:
            for item in await self._search_one(kb, query, top_k):
                marker = (str(item.get("source_name") or ""), str(item.get("evidence") or "")[:120])
                if marker in seen:
                    continue
                seen.add(marker)
                item["query"] = query
                item["source_id"] = self._register_source(item)
                items.append(item)

        if not items:
            return ToolOutcome(
                ok=True,
                summary=f"「{'、'.join(queries)}」没有命中资料",
                payload={"items": [], "kb": kb.name, "count": 0},
            )
        payload = {"items": items, "kb": kb.name, "count": len(items)}
        return ToolOutcome(
            ok=True,
            summary=f"检索 {len(queries)} 组关键词，命中 {len(items)} 条资料",
            payload=payload,
        )

    async def _search_one(self, kb: RdKnowledgeBase, query: str, top_k: int) -> list[dict[str, Any]]:
        """单次检索：事实库优先，但最多占一半预算，剩余强制走 RAGFlow 切片。

        事实库存的是零散字段（CAS、类别、单价），成段的工艺描述与表格都在切片里。
        若让事实库吃满 top_k，查询里带品种名时按置信度取到的永远是那几条通用事实，
        远程切片一次都调不到，模型就会判定「资料里没有」而把整篇正文留空。
        """
        fact_budget = max(1, top_k // 2)
        items = await self._search_facts(kb, query, fact_budget)
        remaining = top_k - len(items)
        if remaining > 0:
            items.extend(await self._search_chunks_remote(kb, query, remaining))
        if not items:
            items.extend(await self._search_chunks_local(kb, query, top_k))
        return items[:top_k]

    def _register_source(self, item: dict[str, Any]) -> str:
        name = str(item.get("source_name") or "").strip() or "未知来源"
        evidence = str(item.get("evidence") or "").strip()
        key = (name, evidence[:120])
        exists = self._source_index.get(key)
        if exists:
            return exists
        self._source_seq += 1
        source_id = f"s{self._source_seq}"
        self._source_index[key] = source_id
        self.sources[source_id] = {"source_name": name, "evidence": evidence}
        return source_id

    async def _resolve_kb(self) -> RdKnowledgeBase | None:
        if self._kb_loaded:
            return self.kb
        self._kb_loaded = True
        result = await self.session.execute(
            select(RdKnowledgeBase)
            .where(
                RdKnowledgeBase.project_id == self.project.id,
                RdKnowledgeBase.is_deleted.is_(False),
            )
            .order_by(RdKnowledgeBase.created_at.desc())
            .limit(1)
        )
        self.kb = result.scalars().first()
        return self.kb

    async def _search_facts(self, kb: RdKnowledgeBase, query: str, top_k: int) -> list[dict[str, Any]]:
        """事实库优先：带 quote 的结构化事实最适合直接落到模板里。"""
        pattern = f"%{query}%"
        terms = [term for term in query.split() if term]
        conditions: list[Any] = [
            RdKbFact.subject.ilike(pattern),
            RdKbFact.predicate.ilike(pattern),
            RdKbFact.value.ilike(pattern),
        ]
        if len(terms) > 1:
            # 逐词兜底只放开 predicate/value：subject 基本都是品种名，放开 subject 会让
            # 「米诺地尔 X Y」命中全部事实，按置信度取到的永远是 CAS/类别/用途那几条。
            conditions.extend(
                or_(RdKbFact.predicate.ilike(f"%{term}%"), RdKbFact.value.ilike(f"%{term}%")) for term in terms
            )
        try:
            result = await self.session.execute(
                select(RdKbFact)
                .where(RdKbFact.kb_id == kb.id, RdKbFact.is_deleted.is_(False), or_(*conditions))
                .order_by(RdKbFact.confidence.desc())
                .limit(top_k)
            )
        except Exception:  # noqa: BLE001 - 知识库查询失败不能让整篇报告失败
            logger.exception("report-gen kb facts query failed", extra={"kb_id": str(kb.id)})
            return []
        return [
            {
                "content": _cut(f"{row.subject} {row.predicate}：{row.value} {row.unit or ''}", 400),
                "evidence": _cut(row.quote, 500),
                "source_name": row.document_name,
                "score": row.confidence,
                "kind": "fact",
            }
            for row in result.scalars().all()
        ]

    async def _search_chunks_remote(self, kb: RdKnowledgeBase, query: str, top_k: int) -> list[dict[str, Any]]:
        if not kb.ragflow_dataset_id:
            return []
        client = RagflowClient()
        if not client.configured:
            return []
        try:
            chunks = await client.retrieval(query, [kb.ragflow_dataset_id], top_k=top_k)
        except Exception:  # noqa: BLE001 - RAGFlow 不可用时退回本地切片
            logger.warning("report-gen ragflow retrieval failed", extra={"kb_id": str(kb.id)})
            return []
        return [
            {
                "content": _cut(chunk.get("content") or chunk.get("content_with_weight"), 800),
                "evidence": _cut(chunk.get("content") or "", 500),
                "source_name": chunk.get("document_keyword") or chunk.get("docnm_kwd") or kb.name,
                "score": chunk.get("similarity") or chunk.get("vector_similarity"),
                "kind": "chunk",
            }
            for chunk in chunks
        ]

    async def _search_chunks_local(self, kb: RdKnowledgeBase, query: str, top_k: int) -> list[dict[str, Any]]:
        pattern = f"%{query}%"
        try:
            result = await self.session.execute(
                select(RdKbChunk)
                .where(RdKbChunk.kb_id == kb.id, RdKbChunk.is_deleted.is_(False), RdKbChunk.content.ilike(pattern))
                .limit(top_k)
            )
        except Exception:  # noqa: BLE001
            logger.exception("report-gen local chunk query failed", extra={"kb_id": str(kb.id)})
            return []
        return [
            {
                "content": _cut(row.content, 800),
                "evidence": _cut(row.content, 500),
                "source_name": row.file_name,
                "score": None,
                "kind": "chunk",
            }
            for row in result.scalars().all()
        ]

    # ------------------------------------------------------------------
    # 工具：写母本既有位置
    # ------------------------------------------------------------------
    def write_paragraph(self, arguments: dict[str, Any]) -> ToolOutcome:
        items, error = self._items(arguments, ("index", "text"))
        if error:
            return ToolOutcome(ok=False, summary=error, payload={"error": error})
        results: list[dict[str, Any]] = []
        ok_count = 0
        for item in items:
            index = _as_int(item.get("index"))
            text = str(item.get("text") or "").strip()
            key = f"p{index}" if index is not None else ""
            position = self.positions.get(key)
            if index is None or position is None:
                results.append(
                    {"key": key or "?", "ok": False, "error": "没有这个段落位置，请用 read_template_outline 确认下标"}
                )
                continue
            if self._human_locked(key):
                results.append({"key": key, "ok": False, "error": "这个位置已由人工确认，保持原文，不要重写"})
                continue
            if not position.writable:
                self.rejected += 1
                results.append({"key": key, "ok": False, "error": position.reason or "这个位置不允许写入"})
                continue
            if not text:
                results.append({"key": key, "ok": False, "error": "text 不能为空"})
                continue
            row = self._upsert_row(
                slot_key=key,
                label=position.label,
                position=position,
                anchor={**position.anchor(), "source_ids": self._source_ids(item)},
                value=_cut(text, _MAX_WRITE_CHARS),
            )
            ok_count += 1
            results.append({"key": key, "ok": True, "where": position.label, "state": row.state})
        return self._write_outcome("写入正文", results, ok_count)

    def write_cell(self, arguments: dict[str, Any]) -> ToolOutcome:
        items, error = self._items(arguments, ("table_index", "row", "col", "text"))
        if error:
            return ToolOutcome(ok=False, summary=error, payload={"error": error})
        results: list[dict[str, Any]] = []
        ok_count = 0
        for item in items:
            table_index = _as_int(item.get("table_index"))
            row_index = _as_int(item.get("row"))
            col_index = _as_int(item.get("col"))
            if table_index is None or row_index is None or col_index is None:
                results.append({"key": "?", "ok": False, "error": "需要 table_index / row / col（从 0 开始）"})
                continue
            key = f"t{table_index}r{row_index}c{col_index}"
            position = self.positions.get(key)
            text = str(item.get("text") or "").strip()
            if position is None:
                results.append(
                    {"key": key, "ok": False, "error": "没有这个单元格，请用 read_template_outline 按表格读取确认行列"}
                )
                continue
            if self._human_locked(key):
                results.append({"key": key, "ok": False, "error": "这个单元格已由人工确认，保持原文，不要重写"})
                continue
            if not position.writable:
                self.rejected += 1
                results.append({"key": key, "ok": False, "error": position.reason or "这个单元格不允许写入"})
                continue
            if not text:
                results.append({"key": key, "ok": False, "error": "text 不能为空"})
                continue
            # 语义校验：这一格是意见栏/CAS号/数值列，值就得对得上。缺这一层，
            # 模型会把「其他名称」写进意见栏、把分子量写进成本列，只有成品才暴露。
            mismatch = validate_cell_value(
                value=text,
                expect=position.expect,
                row_hint=position.row_hint,
                column_hint=position.column_hint,
            )
            if mismatch:
                self.rejected += 1
                results.append({"key": key, "ok": False, "where": position.label, "error": mismatch})
                continue
            row = self._upsert_row(
                slot_key=key,
                label=position.label,
                position=position,
                anchor={**position.anchor(), "source_ids": self._source_ids(item)},
                value=_cut(text, _MAX_WRITE_CHARS),
            )
            ok_count += 1
            results.append({"key": key, "ok": True, "where": position.label, "state": row.state})
        return self._write_outcome("写入表格", results, ok_count)

    # ------------------------------------------------------------------
    # 工具：母本里没有的位置（追加）
    # ------------------------------------------------------------------
    def append_paragraph(self, arguments: dict[str, Any]) -> ToolOutcome:
        """在某个位置之后插入新段落（用于母本路线不够时扩增）。

        ``after`` 可以是母本位置（``p12``、``t2r3c1``）或本次已追加的段落（``ap1``）。
        ``clone_from`` 是要克隆格式的母本段落下标：插入的段落沿用它的样式与字体，
        因此「格式与路线4一致」靠的是复制路线4那两段，而不是让模型写样式名。
        """
        after = str(arguments.get("after") or "").strip()
        if not after:
            return ToolOutcome(
                ok=False,
                summary="after 不能为空",
                payload={"error": "after 需要写成 p12 / ap1 这样的位置标识"},
            )
        # 锚点必须真实存在：写进记录却回放不到，等于白写，还要人工去查为什么少了一段
        if after not in self.positions and after not in self.slot_rows:
            return ToolOutcome(
                ok=False,
                summary=f"after={after} 不是有效位置",
                payload={"error": f"没有 {after} 这个位置，请用 read_template_outline 确认后再插入"},
            )
        # 附件/变更历史/签字审批等整章禁写：追加也是写，不能从这些章节往下插内容
        anchor_position = self.positions.get(after)
        if anchor_position is not None and self.outline.is_fixed_section(anchor_position.section):
            return ToolOutcome(
                ok=False,
                summary=f"{after} 位于「{anchor_position.section}」，该章节整章禁写",
                payload={"error": "目录、附件、变更历史、签字审批区不能追加内容，请换正文位置"},
            )
        items, error = self._items(arguments, ("text",))
        if error:
            return ToolOutcome(ok=False, summary=error, payload={"error": error})

        results: list[dict[str, Any]] = []
        ok_count = 0
        for item in items:
            text = str(item.get("text") or "").strip()
            if not text:
                results.append({"key": after, "ok": False, "error": "text 不能为空"})
                continue
            clone_from = _as_int(item.get("clone_from"))
            if clone_from is None:
                parent = self.positions.get(after)
                if parent is not None and parent.kind == KIND_PARAGRAPH:
                    clone_from = parent.index
                else:
                    results.append({"key": after, "ok": False, "error": "需要 clone_from：要克隆格式的母本段落下标"})
                    continue
            if not 0 <= clone_from < self.outline.paragraph_count:
                results.append({"key": after, "ok": False, "error": f"clone_from={clone_from} 超出母本段落范围"})
                continue

            seq, key = self._next_append_key("ap")
            row = self._upsert_row(
                slot_key=key,
                label=f"追加段落{seq}",
                position=None,
                anchor={
                    "kind": KIND_APPEND_PARAGRAPH,
                    "after": after,
                    "clone_from": clone_from,
                    "seq": seq,
                    "location": f"文末第{seq}段",
                    "source_ids": self._source_ids(item),
                },
                value=_cut(text, _MAX_WRITE_CHARS),
            )
            ok_count += 1
            results.append({"key": key, "ok": True, "after": after, "state": row.state})
        return self._write_outcome(f"在 {after} 之后追加段落", results, ok_count)

    def append_table_rows(self, arguments: dict[str, Any]) -> ToolOutcome:
        """往表格追加行：每行一条记录，参考资料才能说清「这一处写在哪一行」。"""
        table_index = _as_int(arguments.get("table_index"))
        if table_index is None:
            return ToolOutcome(
                ok=False,
                summary="table_index 不能为空",
                payload={"error": "需要 table_index（从 0 开始）"},
            )
        fixed_section = self._table_fixed_section(table_index)
        if fixed_section:
            return ToolOutcome(
                ok=False,
                summary=f"表{table_index + 1} 位于「{fixed_section}」，该章节整章禁写",
                payload={"error": "目录、附件、变更历史、签字审批区不能追加行，请换正文表格"},
            )
        clone_row = _as_int(arguments.get("clone_from_row"))
        items, error = self._items(arguments, ("cells",))
        if error:
            return ToolOutcome(ok=False, summary=error, payload={"error": error})

        results: list[dict[str, Any]] = []
        ok_count = 0
        for item in items:
            cells = item.get("cells")
            if not isinstance(cells, list) or not cells:
                results.append({"key": "?", "ok": False, "error": "cells 必须是字符串数组，按列顺序给值"})
                continue
            seq, key = self._next_append_key("at")
            row = self._upsert_row(
                slot_key=key,
                label=f"表{table_index + 1}追加行{seq}",
                position=None,
                anchor={
                    "kind": KIND_APPEND_TABLE_ROWS,
                    "table_index": table_index,
                    "clone_from_row": clone_row,
                    "seq": seq,
                    "location": f"表{table_index + 1}第{seq}行",
                    "rows": [{"cells": [str(value) for value in cells], "source_ids": self._source_ids(item)}],
                    "source_ids": self._source_ids(item),
                },
                value=_cut(" | ".join(str(value) for value in cells), _MAX_WRITE_CHARS),
            )
            ok_count += 1
            results.append({"key": key, "ok": True, "state": row.state})
        return self._write_outcome(f"表{table_index + 1} 追加行", results, ok_count)

    # ------------------------------------------------------------------
    # 工具：参考资料与收尾
    # ------------------------------------------------------------------
    def append_references(self, arguments: dict[str, Any]) -> ToolOutcome:
        # 参考资料不写进正文，也就不需要 heading；老提示词多传的参数直接忽略
        return self.write_references()

    def write_references(self) -> ToolOutcome:
        """按写入记录去重整理参考资料；重复调用是幂等的，不会产出第二份。

        只落一条 ``ref`` 记录供详情页右栏展示，不写进 Word 正文：
        引用源属于审阅信息，写进母本会挤占版面、还会让成稿多出一章。
        """
        if "ref" in self.slot_rows:
            return ToolOutcome(
                ok=True, summary="参考资料已整理，无需重复调用", payload={"entries": 0, "duplicated": True}
            )
        entries = self.reference_entries()
        if not entries:
            return ToolOutcome(
                ok=False,
                summary="还没有带来源的写入，参考资料为空",
                payload={"error": "先用 search_knowledge_base 拿到 source_id，再在写入时带上 source_ids"},
            )
        row = self._upsert_row(
            slot_key="ref",
            label="参考资料",
            position=None,
            anchor={"kind": KIND_REFERENCES, "entries": entries, "location": "参考资料"},
            value="\n".join(entries),
        )
        logger.info(
            "report-gen references built",
            extra={"job_id": str(self.job.id), "entries": len(entries), "state": row.state},
        )
        return ToolOutcome(
            ok=True,
            summary=f"已整理参考资料，共 {len(entries)} 条来源",
            payload={"entries": len(entries), "preview": entries[:3]},
        )

    def reference_entries(self) -> list[str]:
        """来源 → 落点列表，按首次出现排序；同一来源在正文多处使用时合并成一条。"""
        return format_reference_entries(build_reference_groups(self.slot_rows.values()))

    def finalize(self, arguments: dict[str, Any]) -> ToolOutcome:
        self.finalized = True
        self.final_summary = str(arguments.get("summary") or "").strip()
        # 出稿前复核一遍：实时校验只能拦住写入那一刻，模板换版、后改语义都可能漏网
        mismatches = self.semantic_self_check()
        coverage = self.coverage()
        return ToolOutcome(
            ok=True,
            summary=(
                f"生成结束：已写 {coverage['written']}/{coverage['writable_total']} 处"
                f"，未写空位 {coverage['unwritten']} 处"
                + (f"，被拒绝 {coverage['rejected']} 次" if coverage["rejected"] else "")
                + (f"，{len(mismatches)} 处内容与格子含义不符已标待核对" if mismatches else "")
            ),
            payload={
                **coverage,
                "summary": self.final_summary,
                "unwritten_sample": coverage["unwritten_sample"],
                "semantic_mismatch_sample": mismatches[:10],
            },
        )

    def semantic_self_check(self) -> list[dict[str, Any]]:
        """出稿前语义复核：内容与格子含义不符的位置标成待核对，不改内容。

        实时校验拦的是「写入那一刻」，这一层兜的是「已经写进去的」：模板换版导致行列
        语义变了、人工改过的值不合适、上一版遗留的记录等。标待核对而不是删内容——
        受控文档里丢字比错字更难被发现。
        """
        mismatches: list[dict[str, Any]] = []
        for key, row in self.slot_rows.items():
            position = self.positions.get(key)
            if position is None or position.kind != KIND_TABLE_CELL:
                continue
            value = (row.value or "").strip()
            if not value:
                continue
            # 人工写的以人工为准：不再回头改它的状态，只在清单里保留人工标记
            if str(row.edit_source or "ai") == "manual" or self._human_locked(key):
                continue
            reason = validate_cell_value(
                value=value,
                expect=position.expect,
                row_hint=position.row_hint,
                column_hint=position.column_hint,
            )
            if reason is None:
                continue
            anchor = dict(row.anchor) if isinstance(row.anchor, dict) else {}
            anchor["verify_reason"] = reason
            anchor["verify_kind"] = "semantic"
            row.anchor = anchor
            row.state = "pending"
            mismatches.append({"key": key, "where": position.label, "reason": reason})
            logger.info(
                "report gen cell semantic mismatch",
                extra={
                    "job_id": str(getattr(self.job, "id", "")),
                    "slot_key": key,
                    "table_index": position.index,
                    "biz_module": "research",
                },
            )
        self.semantic_mismatches = mismatches
        return mismatches

    # ------------------------------------------------------------------
    # 覆盖率与内部工具
    # ------------------------------------------------------------------
    def coverage(self) -> dict[str, Any]:
        """本次写入覆盖率：已写位置取自写入记录，分母是母本可写位置总数。

        语义自检命中的位置不算「已填写」：内容在那儿但意思不对，等于还得人补，
        计进已填写只会让覆盖率虚高、把问题藏起来。
        """
        mismatch_keys = {str(item.get("key")) for item in self.semantic_mismatches}
        written_keys = {
            key
            for key, row in self.slot_rows.items()
            if key not in mismatch_keys
            and (row.value or "").strip()
            and str((row.anchor or {}).get("kind") or KIND_PARAGRAPH) in (KIND_PARAGRAPH, KIND_TABLE_CELL)
        }
        writable_total = self.outline.writable_total
        unwritten = [item.key for item in self.outline.writable if item.key not in written_keys]
        return {
            "writable_total": writable_total,
            "written": len(written_keys),
            "unwritten": len(unwritten),
            "rejected": self.rejected,
            # 内容写进去了但与格子含义不符（自检标待核对）的数量，不算「已填写」
            "semantic_mismatch": len(self.semantic_mismatches),
            "appended": sum(
                1
                for row in self.slot_rows.values()
                if str((row.anchor or {}).get("kind") or "") in (KIND_APPEND_PARAGRAPH, KIND_APPEND_TABLE_ROWS)
            ),
            "unwritten_sample": unwritten[:20],
        }

    def _items(
        self, arguments: dict[str, Any], required_keys: tuple[str, ...]
    ) -> tuple[list[dict[str, Any]], str | None]:
        """取批量条目；兼容模型只给单条（不带 items）的写法。"""
        limit = int(getattr(self.config, "write_batch_limit", 10) or 10)
        raw = arguments.get("items")
        if isinstance(raw, list) and raw:
            items = [item for item in raw if isinstance(item, dict)]
            if not items:
                return [], "items 里没有可用的对象"
            if len(items) > limit:
                return [], f"一次最多写 {limit} 处，请拆成多次调用（本次给了 {len(items)} 处）"
            return items, None
        single = {key: arguments.get(key) for key in required_keys if arguments.get(key) not in (None, "")}
        if single and len(single) == len(required_keys):
            return [single], None
        return [], f"缺少 items：请用 items 数组一次提交 1-{limit} 处，每项包含 {'、'.join(required_keys)}"

    def _source_ids(self, item: dict[str, Any]) -> list[str]:
        raw = item.get("source_ids")
        if isinstance(raw, list):
            return [str(value) for value in raw if str(value or "").strip()]
        single = str(raw or "").strip()
        return [single] if single else []

    def _table_fixed_section(self, table_index: int) -> str | None:
        """表格若整张落在固定章节（附件表、变更历史表）里，返回章节名。"""
        for position in self.positions.values():
            if position.kind == KIND_TABLE_CELL and position.index == table_index:
                return position.section if self.outline.is_fixed_section(position.section) else None
        return None

    def _upsert_row(
        self,
        *,
        slot_key: str,
        label: str,
        position: WritablePosition | None,
        anchor: dict[str, Any],
        value: str,
    ) -> RdReportGenSlot:
        """同一位置重复写入时就地覆盖：一个位置只留一条记录，引用源不会重复计数。"""
        ids = [str(item) for item in (anchor.get("source_ids") or []) if str(item or "").strip()]
        names: list[str] = []
        evidence: str | None = None
        for source_id in ids:
            info = self.sources.get(source_id)
            if info is None:
                continue
            name = info.get("source_name") or ""
            if name and name not in names:
                names.append(name)
            evidence = evidence or info.get("evidence")
        anchor["source_names"] = names
        state = "filled" if names else "pending"

        row = self.slot_rows.get(slot_key)
        if row is None:
            row = RdReportGenSlot(
                job_id=self.job.id,
                slot_key=slot_key,
                slot_label=label,
                anchor=anchor,
                value=value,
                state=state,
                source_name="、".join(names)[:500] or None,
                evidence=_cut(evidence, 2000) if evidence else None,
            )
            self.session.add(row)
            self.slot_rows[slot_key] = row
        else:
            row.slot_label = label
            row.anchor = anchor
            row.value = value
            row.state = state
            row.source_name = "、".join(names)[:500] or None
            row.evidence = _cut(evidence, 2000) if evidence else None
        if position is not None:
            row.owner_hint = None
        return row

    @staticmethod
    def _write_outcome(action: str, results: list[dict[str, Any]], ok_count: int) -> ToolOutcome:
        failed = [item for item in results if not item.get("ok")]
        detail = f"{action} {ok_count} 处"
        if failed:
            detail += f"，{len(failed)} 处未写入"
        return ToolOutcome(
            ok=bool(ok_count),
            summary=detail,
            payload={
                "written": ok_count,
                "items": results,
                "errors": [item.get("error") for item in failed][:10],
                "hint": "被拒绝的位置不要重试：换用 read_template_outline 里 writable=true 的位置。"
                if failed
                else None,
            },
        )


# ----------------------------------------------------------------------
# 工具 schema（OpenAI tools 格式，JSON 协议降级时复用同一份定义）
# ----------------------------------------------------------------------
_SOURCE_IDS_SCHEMA = {
    "type": "array",
    "items": {"type": "string"},
    "description": "来源编号，来自 search_knowledge_base 返回的 source_id；会显示在右侧「参考资料」",
}

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_template_outline",
            "description": (
                "读取 Word 母本的可写位置清单（段落 p{下标} 与表格单元格 t{表}r{行}c{列}）。"
                "返回位置标识、所在章节、样式、当前文字、上一段/表头提示，以及是否可写。"
                "开始填写前先看一遍；表格可用 table_index 整表读取。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "offset": {"type": "integer", "description": "分页起始，默认 0"},
                    "limit": {"type": "integer", "description": "每页数量，默认 40，最大 120"},
                    "only_writable": {"type": "boolean", "description": "只列可写位置，默认 true"},
                    "table_index": {"type": "integer", "description": "只看某张表（从 0 开始）"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_project_context",
            "description": "读取研发项目的登记信息、阶段记录、实验记录与本次报告输入（受控编码/品种名称/补充说明）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "section": {
                        "type": "string",
                        "enum": ["all", "basic", "stages", "experiments"],
                        "description": "读取范围，默认 all",
                    }
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": (
                "在项目知识库里检索资料片段，返回内容、来源文件名、原文证据与 source_id。"
                "按章节一次问多个关键词（queries）比逐条问快；返回的 source_id 要传给写入工具。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "单个检索词；与 queries 二选一"},
                    "queries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "一组检索词（最多 5 个），一次查多组",
                    },
                    "top_k": {"type": "integer", "description": "每组返回条数，默认按配置"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_paragraph",
            "description": (
                "把内容写入母本已有的空段落、下划线/XXX 占位段或「标签：」段（只能写 writable=true 的位置）。"
                "append=true 的标签段只给冒号后的值，标签由系统保留，不要重复标签。"
                "一次最多 10 处；标题、完整固定文字、签字页会被拒绝并说明原因，不要重复重试。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "要写入的段落，1-10 项",
                        "items": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "integer", "description": "段落下标，来自 p{n}"},
                                "text": {
                                    "type": "string",
                                    "description": "要写入的内容；多行用 \\n；append=true 的标签段只给冒号后的值",
                                },
                                "source_ids": _SOURCE_IDS_SCHEMA,
                            },
                            "required": ["index", "text"],
                        },
                    }
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_cell",
            "description": "把内容写入表格里空单元格（只能写 writable=true 的位置），行列从 0 开始。一次最多 10 处。",
            "parameters": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "description": "要写入的单元格，1-10 项",
                        "items": {
                            "type": "object",
                            "properties": {
                                "table_index": {"type": "integer", "description": "第几张表，从 0 开始"},
                                "row": {"type": "integer", "description": "行号，从 0 开始"},
                                "col": {"type": "integer", "description": "列号，从 0 开始"},
                                "text": {"type": "string"},
                                "source_ids": _SOURCE_IDS_SCHEMA,
                            },
                            "required": ["table_index", "row", "col", "text"],
                        },
                    }
                },
                "required": ["items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_paragraph",
            "description": (
                "在指定位置之后插入新段落，用于母本条目不够（如只有路线1-4，要写路线5、路线6）。"
                "clone_from 是要克隆格式的母本段落下标：格式与那一段完全一致，不新建样式。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "after": {
                        "type": "string",
                        "description": "插在谁之后：母本位置 p{下标}/t{表}r{行}c{列}，或本次追加的 ap{n}",
                    },
                    "items": {
                        "type": "array",
                        "description": "要插入的段落，1-10 项（按顺序插在 after 之后）",
                        "items": {
                            "type": "object",
                            "properties": {
                                "text": {"type": "string"},
                                "clone_from": {
                                    "type": "integer",
                                    "description": "克隆格式用的母本段落下标（如路线4的标题段/内容段）",
                                },
                                "source_ids": _SOURCE_IDS_SCHEMA,
                            },
                            "required": ["text", "clone_from"],
                        },
                    },
                },
                "required": ["after", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_table_rows",
            "description": (
                "往表格末尾追加行：深拷贝 clone_from_row 那一行的格式（边框/行高/底色），"
                "再按 cells 顺序填值。cells 的列数要与表格列数一致。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "table_index": {"type": "integer", "description": "第几张表，从 0 开始"},
                    "clone_from_row": {"type": "integer", "description": "克隆格式用的行号，默认取最后一行"},
                    "items": {
                        "type": "array",
                        "description": "要追加的行，1-10 项",
                        "items": {
                            "type": "object",
                            "properties": {
                                "cells": {"type": "array", "items": {"type": "string"}},
                                "source_ids": _SOURCE_IDS_SCHEMA,
                            },
                            "required": ["cells"],
                        },
                    },
                },
                "required": ["table_index", "items"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "append_references",
            "description": (
                "按本次写入记录整理「参考资料」（按来源去重，显示在页面右侧，不写进 Word 正文）。"
                "全部写完后调用一次即可。"
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize",
            "description": "全部位置处理完后调用，结束生成并触发出稿；会回报覆盖率（已写/未写/被拒）。",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string", "description": "本次填写的一句话总结"}},
            },
        },
    },
]

TOOL_NAMES = tuple(spec["function"]["name"] for spec in TOOL_SPECS)

# 收尾工具不能关：关掉后模型永远无法声明完成，任务只能等轮次上限耗尽
ALWAYS_ENABLED_TOOLS = frozenset({"finalize"})


def _normalize_disabled(disabled: frozenset[str] | set[str] | tuple[str, ...] | None) -> frozenset[str]:
    return frozenset(item.strip().lower() for item in (disabled or ()) if item.strip())


def is_tool_enabled(name: str, disabled: frozenset[str] | set[str] | None = None) -> bool:
    """工具是否启用；``ALWAYS_ENABLED_TOOLS`` 无视禁用清单。"""
    if name in ALWAYS_ENABLED_TOOLS:
        return True
    return name.lower() not in _normalize_disabled(disabled)


def resolve_tool_specs(disabled: frozenset[str] | set[str] | None = None) -> list[dict[str, Any]]:
    """按禁用清单过滤下发给模型的工具目录。

    禁用后模型既看不到该工具的 schema，也无法在 JSON 协议里调用它；下发与执行
    两处用同一份清单，避免「协议里有、执行时被拒」的反复试探。
    """
    blocked = _normalize_disabled(disabled) - ALWAYS_ENABLED_TOOLS
    if not blocked:
        return TOOL_SPECS
    return [spec for spec in TOOL_SPECS if spec["function"]["name"] not in blocked]


def required_arguments(name: str) -> tuple[str, ...]:
    """某工具的必填参数（来自工具 schema，避免和实际校验两处漂移）。"""
    for spec in TOOL_SPECS:
        function = spec["function"]
        if function["name"] == name:
            return tuple(function["parameters"].get("required") or ())
    return ()


async def execute_tool(name: str, arguments: dict[str, Any], runtime: ReportGenRuntime) -> ToolOutcome:
    """按名字分派工具；未知名与执行异常都收敛成 failed 结果。

    只在命中时取 handler：提前把所有 handler 全取出来，任何一个没接上都会变成
    整条链路的 ``AttributeError``，而不是一条失败步骤 —— 那会中断整份报告的生成。
    """
    if name not in TOOL_NAMES:
        return ToolOutcome(ok=False, summary=f"未知工具 {name}", payload={"error": f"未知工具 {name}"})
    # 纵深防御：schema 已过滤，但 JSON 协议下模型仍可能凭历史记忆直接点名调用
    config = getattr(runtime, "config", None)
    if not is_tool_enabled(name, getattr(config, "disabled_tools", None)):
        return ToolOutcome(
            ok=False,
            summary=f"工具 {name} 已被管理员停用",
            payload={"error": f"工具 {name} 当前不可用，请用其他工具或跳过该位置"},
        )
    handler = getattr(runtime, name, None)
    if not callable(handler):
        return ToolOutcome(ok=False, summary=f"工具 {name} 未就绪", payload={"error": f"工具 {name} 未就绪"})

    # 实测模型会发出空参数调用（如 search_knowledge_base({})）；不拦住就变成
    # 一条含糊的「query 不能为空」，模型往往原样重试，白烧轮次。这里明确点名缺哪些参数。
    wanted = required_arguments(name)
    missing = [key for key in wanted if arguments.get(key) in (None, "", [], {})]
    if missing:
        return ToolOutcome(
            ok=False,
            summary=f"{name} 缺少必填参数：{'、'.join(missing)}",
            payload={
                "error": f"缺少必填参数：{'、'.join(missing)}",
                "required": list(wanted),
                "hint": "按 required 补齐参数后重新调用，空参数调用不会被执行。",
            },
        )
    try:
        # 工具既可同步也可异步；统一在这里收口，避免调用方关心实现细节
        outcome = handler(arguments)
        if inspect.isawaitable(outcome):
            return cast(ToolOutcome, await outcome)
        return cast(ToolOutcome, outcome)
    except Exception as exc:  # noqa: BLE001 - 工具失败记入步骤，不中断任务
        logger.exception("report-gen tool failed", extra={"tool": name})
        return ToolOutcome(ok=False, summary=f"{name} 执行失败：{exc}", payload={"error": str(exc)})


__all__ = [
    "ALWAYS_ENABLED_TOOLS",
    "MAX_OUTLINE_TEXT",
    "TOOL_NAMES",
    "TOOL_SPECS",
    "ReportGenRuntime",
    "ToolOutcome",
    "execute_tool",
    "is_tool_enabled",
    "resolve_tool_specs",
]
