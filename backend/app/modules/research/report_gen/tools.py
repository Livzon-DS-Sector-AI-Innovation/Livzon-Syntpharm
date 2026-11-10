"""Agent 可调用的工具集。

工具是「模型能看见的世界边界」：模板槽位、项目上下文、项目知识库、写入槽位。
每个工具都返回 ``ToolOutcome``（一句话摘要给步骤流看 + 结构化结果给模型看），
并且**不抛异常给上层**——工具失败本身是执行过程的一部分，记录后让模型继续。
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

logger = logging.getLogger(__name__)

# 交给模型的输出上限：既控制 context 长度，也避免步骤表被长文本撑爆
_MAX_TOOL_TEXT = 1500
_PENDING_CONFIDENCE = 0.6


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


class ReportGenRuntime:
    """一次任务内的工具执行上下文（持有 session、任务行、槽位行）。"""

    def __init__(
        self,
        session: AsyncSession,
        job: RdReportGenJob,
        project: RdProject,
        structure: dict[str, Any],
        slot_rows: dict[str, RdReportGenSlot],
        config: Any,
        *,
        report_title: str = "",
        examples: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.session = session
        self.job = job
        self.report_title = report_title
        self.project = project
        self.structure = structure
        self.slot_rows = slot_rows
        self.config = config
        # 人工修正沉淀的示例：随槽位一起下发，模型照着写而不是从零猜
        self.examples = examples or {}
        self.finalized = False
        self.final_summary = ""
        self.kb: RdKnowledgeBase | None = None
        self._kb_loaded = False

    # ------------------------------------------------------------------
    # 工具：读模板
    # ------------------------------------------------------------------
    def read_template_outline(self, arguments: dict[str, Any]) -> ToolOutcome:
        offset = max(int(arguments.get("offset") or 0), 0)
        limit = min(max(int(arguments.get("limit") or 40), 1), 80)
        slots = self.structure.get("slots") or []
        page = slots[offset : offset + limit]
        items = []
        for slot in page:
            key = str(slot.get("slot_key") or "")
            row = self.slot_rows.get(key)
            item: dict[str, Any] = {
                "slot_key": key,
                "label": slot.get("label"),
                "location": slot.get("location"),
                "value_type": slot.get("value_type"),
                "hint": slot.get("hint"),
                "owner_hint": slot.get("owner_hint"),
                "state": row.state if row else "pending",
                "current_value": _cut(row.value, 200) if row and row.value else "",
            }
            example = self.examples.get(key)
            if example:
                # 标明这是「以前人工写过的」：不是依据，不能直接当 evidence 用
                item["manual_example"] = {
                    "value": example.get("value"),
                    "evidence": example.get("evidence"),
                    "note": "人工修正过的历史写法，可参考措辞；引用仍须以检索到的原文为依据",
                }
            items.append(item)
        return ToolOutcome(
            ok=True,
            summary=f"返回填充项 {offset + 1}-{offset + len(items)} / 共 {len(slots)} 个",
            payload={
                "total": len(slots),
                "offset": offset,
                "slots": items,
                "note": "还有没列出的填充项，用更大的 offset 继续读取" if offset + limit < len(slots) else None,
            },
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
        query = str(arguments.get("query") or "").strip()
        if not query:
            return ToolOutcome(ok=False, summary="query 不能为空", payload={"error": "query 不能为空"})
        top_k = min(max(int(arguments.get("top_k") or self.config.kb_top_k), 1), 12)

        kb = await self._resolve_kb()
        if kb is None:
            return ToolOutcome(
                ok=False,
                summary="这个项目还没有知识库，没查到资料",
                payload={"error": "这个项目还没有知识库", "items": []},
            )

        items: list[dict[str, Any]] = []
        items.extend(await self._search_facts(kb, query, top_k))
        if len(items) < top_k:
            items.extend(await self._search_chunks_remote(kb, query, top_k - len(items)))
        if not items:
            items.extend(await self._search_chunks_local(kb, query, top_k))

        payload = {"items": items[:top_k], "kb": kb.name, "count": len(items[:top_k])}
        return ToolOutcome(
            ok=True,
            summary=f"「{query}」命中 {payload['count']} 条资料",
            payload=payload,
        )

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
            conditions.extend(or_(RdKbFact.subject.ilike(f"%{t}%"), RdKbFact.predicate.ilike(f"%{t}%")) for t in terms)
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
    # 工具：写槽位
    # ------------------------------------------------------------------
    def fill_slot(self, arguments: dict[str, Any]) -> ToolOutcome:
        slot_key = str(arguments.get("slot_key") or "").strip()
        value = str(arguments.get("value") or "").strip()
        row = self.slot_rows.get(slot_key)
        if row is None:
            return ToolOutcome(ok=False, summary=f"没有叫 {slot_key} 的填充项", payload={"error": "没有这个填充项"})
        if not value:
            return ToolOutcome(ok=False, summary=f"{slot_key} 没有填内容", payload={"error": "value 不能为空"})

        evidence = str(arguments.get("evidence") or "").strip()
        source_name = str(arguments.get("source_name") or "").strip()
        confidence = arguments.get("confidence")
        try:
            parsed_confidence = float(confidence) if confidence is not None else None
        except (TypeError, ValueError):
            parsed_confidence = None

        previous = (row.value or "").strip()
        conflict = bool(previous) and previous != value
        if conflict:
            row.state = "conflict"
            row.evidence = _cut(f"{row.evidence or ''}\n另见：{evidence}", 2000)
        elif parsed_confidence is not None and parsed_confidence < _PENDING_CONFIDENCE:
            row.state = "pending"
        elif not evidence and not source_name:
            # 无出处的值仍可用，但标记待确认，避免对照表里出现「无来源的已填」
            row.state = "pending"
        else:
            row.state = "filled"
        row.value = value
        row.source_name = source_name[:500] or row.source_name
        if not conflict:
            row.evidence = _cut(evidence, 2000)
        row.confidence = parsed_confidence

        return ToolOutcome(
            ok=True,
            summary=f"{row.slot_label or slot_key} ← {_cut(value, 60)}（{row.state}）",
            payload={"slot_key": slot_key, "state": row.state, "conflict": conflict},
        )

    def mark_gap(self, arguments: dict[str, Any]) -> ToolOutcome:
        slot_key = str(arguments.get("slot_key") or "").strip()
        row = self.slot_rows.get(slot_key)
        if row is None:
            return ToolOutcome(ok=False, summary=f"没有叫 {slot_key} 的填充项", payload={"error": "没有这个填充项"})
        owner = str(arguments.get("owner_hint") or "").strip() or (row.owner_hint or "")
        reason = str(arguments.get("reason") or "").strip()
        row.state = "gap"
        row.value = None
        row.owner_hint = owner[:100] or None
        row.evidence = _cut(reason, 2000) if reason else row.evidence
        return ToolOutcome(
            ok=True,
            summary=f"{row.slot_label or slot_key} 标为待补充（{owner or '责任方待定'}）",
            payload={"slot_key": slot_key, "state": "gap", "owner_hint": row.owner_hint},
        )

    def finalize(self, arguments: dict[str, Any]) -> ToolOutcome:
        self.finalized = True
        self.final_summary = str(arguments.get("summary") or "").strip()
        filled = sum(1 for row in self.slot_rows.values() if row.state in ("filled", "conflict"))
        gaps = sum(1 for row in self.slot_rows.values() if row.state in ("gap", "pending"))
        return ToolOutcome(
            ok=True,
            summary=f"生成结束：已填 {filled} 项，待补充/待确认 {gaps} 项",
            payload={"filled": filled, "gaps": gaps, "summary": self.final_summary},
        )


# ----------------------------------------------------------------------
# 工具 schema（OpenAI tools 格式，JSON 协议降级时复用同一份定义）
# ----------------------------------------------------------------------
TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "read_template_outline",
            "description": "读取 Word 母本的槽位清单（附当前填充状态）。开始填写前先调用它了解要填哪些位置。",
            "parameters": {
                "type": "object",
                "properties": {
                    "offset": {"type": "integer", "description": "分页起始，默认 0"},
                    "limit": {"type": "integer", "description": "每页数量，默认 40，最大 80"},
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
            "description": "在项目知识库里检索资料片段，返回内容、来源文件名与原文证据。填槽位前用它找依据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "检索词，用槽位含义或有业务含义的短句"},
                    "top_k": {"type": "integer", "description": "返回条数，默认按配置"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fill_slot",
            "description": "把值写入一个槽位。必须给出出处（source_name）与原文证据（evidence）。",
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_key": {"type": "string", "description": "槽位标识，来自槽位清单"},
                    "value": {"type": "string", "description": "要写入模板的内容"},
                    "source_name": {"type": "string", "description": "来源文件或数据表名"},
                    "evidence": {"type": "string", "description": "支撑该值的原文引用（原样摘录）"},
                    "confidence": {"type": "number", "description": "置信度 0~1"},
                },
                "required": ["slot_key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "mark_gap",
            "description": "资料确实找不到时标记缺口，模板里会写「待补充：责任方」。",
            "parameters": {
                "type": "object",
                "properties": {
                    "slot_key": {"type": "string"},
                    "owner_hint": {"type": "string", "description": "应找哪个部门补充"},
                    "reason": {"type": "string", "description": "缺什么、查过哪些来源"},
                },
                "required": ["slot_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalize",
            "description": "全部槽位处理完后调用，结束生成并触发出稿。",
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

    只在命中时取 handler：提前把 6 个 handler 全取出来，任何一个没接上都会变成
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
            payload={"error": f"工具 {name} 当前不可用，请用其他工具或标记缺口"},
        )
    handler = getattr(runtime, name, None)
    if not callable(handler):
        return ToolOutcome(ok=False, summary=f"工具 {name} 未就绪", payload={"error": f"工具 {name} 未就绪"})

    # 实测模型会发出空参数调用（如 search_knowledge_base({})）；不拦住就变成
    # 一条含糊的「query 不能为空」，模型往往原样重试，白烧轮次。这里明确点名缺哪些参数。
    wanted = required_arguments(name)
    missing = [key for key in wanted if not str(arguments.get(key) or "").strip()]
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
    "TOOL_NAMES",
    "TOOL_SPECS",
    "ReportGenRuntime",
    "ToolOutcome",
    "execute_tool",
    "is_tool_enabled",
    "resolve_tool_specs",
]
