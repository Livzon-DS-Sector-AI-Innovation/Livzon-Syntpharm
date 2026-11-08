"""Agent 循环：让模型自主决定「读模板 → 查资料 → 填槽位 → 收尾」。

两种协议：
- ``tools``：OpenAI 兼容 tool calling，模型直接产出 tool_calls（首选）；
- ``json``：模型每轮输出 ``{"thought","action","action_input"}``（端点不支持 tools 时降级）。

无论走哪种，每一步都写进 ``rd_report_gen_steps``：这是详情页「执行过程」的唯一
数据源，也是事后追溯「这条结论从哪来」的依据。工具失败不抛给上层，只记一条
failed 步骤，让模型自己决定改用别的资料或标缺口。
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.core.llm import llm_client
from app.core.llm.exceptions import LLMError, LLMToolsUnsupportedError
from app.modules.research.doc_template import store
from app.modules.research.models import (
    RdDeliverableTemplate,
    RdProject,
    RdReport,
    RdReportGenJob,
    RdReportGenSlot,
    RdReportGenStep,
)
from app.modules.research.report_gen.config import ReportGenConfig, load_config
from app.modules.research.report_gen.model_binding import ModelBinding, resolve_bindings
from app.modules.research.report_gen.render import SlotFill, render_document
from app.modules.research.report_gen.structure import enabled_slots, ensure_structure
from app.modules.research.report_gen.tools import (
    ReportGenRuntime,
    ToolOutcome,
    execute_tool,
    resolve_tool_specs,
)

logger = logging.getLogger(__name__)

_MAX_ARGS_CHARS = 1000
_MAX_RESULT_CHARS = 2000

_SYSTEM_PROMPT = """你是原料药研发部的报告编写助手。你要基于**项目已有资料**填写一份 Word 报告模板。

工作方式：
1. 先调用 read_template_outline 看清要填哪些槽位（可分页读取）；
2. 调用 read_project_context 拿项目登记信息、阶段记录、实验记录；
3. 针对每个槽位，用 search_knowledge_base 找资料（检索词用槽位含义，不要照抄槽位名）；
4. 找到依据就 fill_slot，必须带 source_name 与 evidence（原文摘录，不得改写）；
5. 确实找不到就 mark_gap，并给出应补充的部门；
6. 所有槽位都处理完后调用 finalize。

硬性要求：
- 绝不编造数据、批号、日期、数值；没有依据一律 mark_gap。
- 品种名称、受控编码、报告标题以本次报告输入为准，项目登记数据可补全 API 名称、CAS 号等。
- 同一信息可复用于多个语义相同的槽位。
- 一次可以并行发起多个工具调用；不要重复检索同样的内容。
- 除工具调用外，用一句中文说明你正在做什么。"""

_JSON_PROTOCOL_PROMPT = """当前模型以 JSON 协议工作：每轮只输出一个 JSON 对象，不要输出别的文字。
调用工具：{"thought":"一句话说明","action":"工具名","action_input":{...}}
全部完成：{"thought":"一句话说明","final":true,"summary":"本次填写总结"}
可用工具（JSON schema）：{tools}
工具执行结果会以 {"tool_result": ...} 的形式回给你。"""


def _cut(text: Any, limit: int) -> str:
    value = "" if text is None else str(text)
    return value if len(value) <= limit else value[:limit] + "…"


def _summarize_args(arguments: dict[str, Any]) -> dict[str, Any]:
    """步骤表里的入参摘要：长字符串截断，避免把整段资料原文写进轨迹。"""
    summary: dict[str, Any] = {}
    for key, value in arguments.items():
        if isinstance(value, str):
            summary[str(key)] = _cut(value, 300)
        elif isinstance(value, (int, float, bool)) or value is None:
            summary[str(key)] = value
        else:
            summary[str(key)] = _cut(json.dumps(value, ensure_ascii=False), 300)
    return summary


def _utcnow() -> datetime:
    return datetime.now(UTC)


class _StepWriter:
    """执行轨迹写入器：只追加，seq 连续，超上限后只保留状态行。"""

    def __init__(self, session: AsyncSession, job: RdReportGenJob, max_steps: int) -> None:
        self.session = session
        self.job = job
        self.max_steps = max_steps
        self.seq = 0

    async def add(
        self,
        kind: str,
        title: str,
        *,
        tool_name: str | None = None,
        arguments: dict[str, Any] | None = None,
        result: str | None = None,
        status: str = "ok",
        duration_ms: int | None = None,
    ) -> None:
        self.seq += 1
        if self.seq > self.max_steps and kind != "status":
            return
        self.session.add(
            RdReportGenStep(
                job_id=self.job.id,
                seq=self.seq,
                kind=kind,
                title=_cut(title, 300),
                tool_name=tool_name,
                args_summary=_summarize_args(arguments) if arguments else None,
                result_summary=_cut(result, _MAX_RESULT_CHARS) if result else None,
                status=status,
                duration_ms=duration_ms,
            )
        )
        await self.session.commit()

    async def progress(self, current_step: str, progress: int) -> None:
        self.job.current_step = _cut(current_step, 300)
        self.job.progress = max(0, min(progress, 100))
        await self.session.commit()


async def _load_job(session: AsyncSession, job_id: UUID) -> RdReportGenJob | None:
    result = await session.execute(
        select(RdReportGenJob).where(RdReportGenJob.id == job_id, RdReportGenJob.is_deleted.is_(False))
    )
    return result.scalars().first()


async def _cancel_requested(session: AsyncSession, job_id: UUID) -> bool:
    value = await session.scalar(select(RdReportGenJob.cancel_requested).where(RdReportGenJob.id == job_id))
    return bool(value)


def _slot_progress(slot_rows: dict[str, RdReportGenSlot]) -> tuple[int, int, int]:
    total = len(slot_rows)
    done = sum(1 for row in slot_rows.values() if row.state in ("filled", "conflict", "gap"))
    filled = sum(1 for row in slot_rows.values() if row.state in ("filled", "conflict"))
    return total, done, filled


def _apply_slot_progress(job: RdReportGenJob, slot_rows: dict[str, RdReportGenSlot]) -> None:
    """把槽位填充情况同步到任务行，出稿前后各刷一次，前端轮询据此展示进度。"""
    total, _done, filled = _slot_progress(slot_rows)
    job.slot_total = total
    job.slot_filled = filled
    job.slot_gap = sum(1 for row in slot_rows.values() if row.state in ("gap", "pending", "anchor_unresolved"))


async def _ensure_slot_rows(
    session: AsyncSession, job: RdReportGenJob, structure: dict[str, Any]
) -> dict[str, RdReportGenSlot]:
    """为模板的每个槽位建一行（幂等：重跑任务沿用已有行）。"""
    existing = await session.execute(
        select(RdReportGenSlot).where(RdReportGenSlot.job_id == job.id, RdReportGenSlot.is_deleted.is_(False))
    )
    rows = {row.slot_key: row for row in existing.scalars().all()}
    for slot in structure.get("slots") or []:
        key = str(slot.get("slot_key") or "")
        if not key or key in rows:
            continue
        anchor = dict(slot.get("anchor") or {})
        anchor["location"] = slot.get("location")
        row = RdReportGenSlot(
            job_id=job.id,
            slot_key=key,
            slot_label=str(slot.get("label") or ""),
            anchor=anchor,
            state="pending",
            owner_hint=slot.get("owner_hint"),
        )
        session.add(row)
        rows[key] = row
    await session.flush()
    job.slot_total = len(rows)
    return rows


def _slot_fill(row: RdReportGenSlot) -> SlotFill:
    return SlotFill(
        slot_key=row.slot_key,
        label=row.slot_label,
        anchor=row.anchor,
        location=str((row.anchor or {}).get("location") or "") or None,
        value=row.value,
        state=row.state,
        source_name=row.source_name,
        evidence=row.evidence,
        owner_hint=row.owner_hint,
    )


def _build_messages(
    job: RdReportGenJob, project: RdProject, report: RdReport, structure: dict[str, Any]
) -> list[dict[str, Any]]:
    slots = structure.get("slots") or []
    user_prompt = (
        "## 本次报告\n"
        f"- 标题：{report.title}\n"
        f"- 类型：{report.report_type}\n"
        f"- 阶段：{report.stage}\n"
        f"- 版本：{report.version}\n"
        f"- 受控编码：{job.doc_code or '（未填写）'}\n"
        f"- 品种名称：{job.drug_name or project.name}\n"
        f"- 补充说明：{job.supplement_text or '（无）'}\n\n"
        f"## 项目\n- 名称：{project.name}\n- API 名称：{project.api_name}\n\n"
        f"## 模板\n- 槽位数量：{len(slots)}\n"
        "请开始：先读取槽位清单，再逐个查找资料并填写。"
    )
    return [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]


class _ModelSwitch:
    """一次任务内的当前模型档位。

    主档失败切到兜底后保持切换，后续轮次不再反复撞同一个坏端点；是否降级同步写进
    ``job.used_fallback``，供详情页标注「已降级」。
    """

    def __init__(self, main: ModelBinding, fallback: ModelBinding) -> None:
        self.main = main
        self.fallback = fallback
        self.current = main
        self.switched = False


async def _call_llm[T](
    switch: _ModelSwitch,
    job: RdReportGenJob,
    steps: _StepWriter,
    call: Callable[[ModelBinding], Awaitable[T]],
) -> T:
    """执行一次 LLM 调用；主档失败且配了兜底时切换一次并重试。

    ``LLMToolsUnsupportedError`` 不算模型故障：它是协议能力问题，必须抛回上层去做
    tools → json 的降级；把它当失败会拿兜底模型重复撞同一个协议限制。
    """
    try:
        return await call(switch.current)
    except LLMToolsUnsupportedError:
        raise
    except (LLMError, TimeoutError) as exc:
        if switch.switched or switch.fallback.is_empty:
            raise
        switch.switched = True
        switch.current = switch.fallback
        job.used_fallback = True
        logger.warning(
            "report-gen fallback model switch",
            extra={
                "job_id": str(job.id),
                "from": switch.main.display,
                "to": switch.fallback.display,
                "error": str(exc)[:200],
            },
        )
        await steps.add(
            "status",
            f"主模型 {switch.main.display or '默认'} 调用失败，已切换兜底模型 {switch.fallback.display}",
            status="failed",
        )
        return await call(switch.current)


async def _run_tools_round(
    session: AsyncSession,
    messages: list[dict[str, Any]],
    runtime: ReportGenRuntime,
    steps: _StepWriter,
    config: ReportGenConfig,
    switch: _ModelSwitch,
    tool_specs: list[dict[str, Any]],
) -> bool:
    """跑一轮 tool-calling，返回模型本轮是否结束。"""
    response = await _call_llm(
        switch,
        runtime.job,
        steps,
        lambda binding: asyncio.wait_for(
            llm_client.chat_with_tools(
                messages,
                tool_specs,
                temperature=0.2,
                **binding.call_kwargs(),
            ),
            timeout=config.llm_timeout_seconds,
        ),
    )
    if response.content.strip():
        await steps.add("think", _cut(response.content.strip(), 200), result=response.content.strip())

    if not response.tool_calls:
        messages.append({"role": "assistant", "content": response.content or ""})
        messages.append(
            {"role": "user", "content": "请继续：要填写槽位就调用工具；全部处理完调用 finalize。"}
        )
        return runtime.finalized

    messages.append(
        {
            "role": "assistant",
            "content": response.content or None,
            "tool_calls": [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": call.arguments_raw or "{}"},
                }
                for call in response.tool_calls
            ],
        }
    )

    for call in response.tool_calls:
        await steps.add(
            "tool_call",
            f"调用 {call.name}",
            tool_name=call.name,
            arguments=call.arguments,
        )
        started = time.monotonic()
        outcome = await asyncio.wait_for(
            execute_tool(call.name, call.arguments, runtime),
            timeout=config.tool_timeout_seconds,
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        await _record_outcome(steps, call.name, call.arguments, outcome, elapsed_ms)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": call.id,
                "content": json.dumps(
                    {"ok": outcome.ok, "summary": outcome.summary, "result": outcome.payload},
                    ensure_ascii=False,
                ),
            }
        )
        if runtime.finalized:
            break
    await session.commit()
    return runtime.finalized


async def _record_outcome(
    steps: _StepWriter,
    name: str,
    arguments: dict[str, Any],
    outcome: ToolOutcome,
    elapsed_ms: int,
) -> None:
    await steps.add(
        "tool_result",
        outcome.summary,
        tool_name=name,
        arguments=arguments,
        result=json.dumps(outcome.payload, ensure_ascii=False, default=str),
        status="ok" if outcome.ok else "failed",
        duration_ms=elapsed_ms,
    )


async def _run_json_round(
    messages: list[dict[str, Any]],
    runtime: ReportGenRuntime,
    steps: _StepWriter,
    config: ReportGenConfig,
    switch: _ModelSwitch,
) -> bool:
    """JSON-action 协议（ReAct）：模型只输出一个 JSON 动作。"""
    raw = await _call_llm(
        switch,
        runtime.job,
        steps,
        lambda binding: asyncio.wait_for(
            llm_client.chat_json(
                messages,
                temperature=0.2,
                **binding.call_kwargs(),
            ),
            timeout=config.llm_timeout_seconds,
        ),
    )
    thought = _cut(raw.get("thought") or "", 300)
    if thought:
        await steps.add("think", thought, result=thought)

    messages.append({"role": "assistant", "content": json.dumps(raw, ensure_ascii=False)})

    if raw.get("final") is True:
        runtime.finalized = True
        runtime.final_summary = str(raw.get("summary") or "")
        await steps.add("status", "模型声明填写完成", result=runtime.final_summary)
        return True

    action = str(raw.get("action") or "").strip()
    action_input = raw.get("action_input")
    arguments = action_input if isinstance(action_input, dict) else {}
    if not action:
        messages.append({"role": "user", "content": '{"tool_result": {"ok": false, "error": "缺少 action"}}'})
        return False

    await steps.add("tool_call", f"调用 {action}", tool_name=action, arguments=arguments)
    started = time.monotonic()
    outcome = await asyncio.wait_for(
        execute_tool(action, arguments, runtime),
        timeout=config.tool_timeout_seconds,
    )
    elapsed_ms = int((time.monotonic() - started) * 1000)
    await _record_outcome(steps, action, arguments, outcome, elapsed_ms)
    messages.append(
        {
            "role": "user",
            "content": json.dumps(
                {"tool_result": {"ok": outcome.ok, "summary": outcome.summary, "result": outcome.payload}},
                ensure_ascii=False,
            ),
        }
    )
    return runtime.finalized


def resolve_initial_mode(tool_mode: str) -> str:
    """首轮协议：auto 与 tools 都先走 tools，只有显式 json 才直接走 JSON。

    之前 auto 落到 else 分支直接跑 JSON 协议，等于从未尝试 tools：模型在
    塞满 TOOL_SPECS 的 JSON 模板里乱猜参数，实测 16 轮 0 填充。
    """
    return "json" if tool_mode == "json" else "tools"


async def _close_untouched_slots(slot_rows: dict[str, RdReportGenSlot]) -> None:
    """没被模型处理的槽位统一按缺口收口，保证对照表完整、模板不出现空白。"""
    for row in slot_rows.values():
        if row.state == "pending" and not (row.value or "").strip():
            row.state = "gap"


async def _render_and_store(
    session: AsyncSession,
    job: RdReportGenJob,
    report: RdReport,
    template: RdDeliverableTemplate | None,
    slot_rows: dict[str, RdReportGenSlot],
    steps: _StepWriter,
) -> None:
    if not job.template_file_key:
        raise RuntimeError("任务缺少母本存储键，无法出稿")
    template_bytes = store.load_bytes(job.template_file_key)
    if not template_bytes:
        raise RuntimeError("母本文件已丢失，无法出稿")

    fills = [_slot_fill(row) for row in slot_rows.values()]
    meta = {
        "title": report.title,
        "doc_code": job.doc_code,
        "drug_name": job.drug_name,
        "template_name": template.name if template else "",
    }
    output = render_document(template_bytes, fills, meta=meta)

    for key in output.unresolved:
        row = slot_rows.get(key)
        if row is not None:
            row.state = "anchor_unresolved"

    safe_title = (report.title or "report").replace("/", "_")[:60]
    job.document_file_name = f"{safe_title}.docx"
    job.document_object_key = store.save_bytes(
        job.document_file_name,
        output.document,
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    job.comparison_object_key = store.save_bytes(
        f"{safe_title}-槽位对照表.md",
        output.comparison_markdown.encode("utf-8"),
        "text/markdown; charset=utf-8",
    )
    await steps.add(
        "status",
        f"成品已生成：写入 {output.filled} 个槽位，缺口 {output.gaps} 个",
        result=f"未定位槽位：{', '.join(output.unresolved) if output.unresolved else '无'}",
    )
    await session.commit()


async def _execute(session: AsyncSession, job: RdReportGenJob, config: ReportGenConfig) -> None:
    report = await session.get(RdReport, job.report_id)
    project = await session.get(RdProject, job.project_id)
    if report is None or project is None:
        raise RuntimeError("报告或研发项目不存在，无法生成")

    template = None
    if job.deliverable_template_id:
        template = await session.get(RdDeliverableTemplate, job.deliverable_template_id)
    if template is None:
        raise RuntimeError("该报告没有关联交付物模板，无法生成")

    job.status = "running"
    job.started_at = _utcnow()
    job.progress = 2
    job.current_step = "解析 Word 母本结构"
    await session.commit()

    steps = _StepWriter(session, job, config.max_steps)
    await steps.add("status", "任务开始：解析 Word 母本结构")

    structure = await ensure_structure(session, template, config)
    await session.commit()

    # 人工停用的槽位在这一步过滤掉：不建槽位行、不下发给模型、也不回写，
    # 下游 render 只吃 slot_rows，因此单点过滤即可覆盖全部路径。
    # 只影响本次任务，历史任务已有的槽位行不回改。
    enabled_structure = {**structure, "slots": enabled_slots(structure)}
    disabled_count = len(structure.get("slots") or []) - len(enabled_structure["slots"])
    await steps.add(
        "status",
        f"母本解析完成，识别到 {len(enabled_structure['slots'])} 个槽位"
        + (f"（已按配置停用 {disabled_count} 个）" if disabled_count else ""),
        result=json.dumps(
            [slot.get("label") for slot in enabled_structure["slots"]][:40], ensure_ascii=False
        ),
    )
    if disabled_count:
        logger.info(
            "report gen skipped disabled slots",
            extra={"job_id": str(job.id), "disabled_slots": disabled_count},
        )

    slot_rows = await _ensure_slot_rows(session, job, enabled_structure)
    await session.commit()

    runtime = ReportGenRuntime(
        session,
        job,
        project,
        enabled_structure,
        slot_rows,
        config,
        report_title=report.title,
    )
    messages = _build_messages(job, project, report, enabled_structure)
    # 工具清单在任务开始时算一次：禁用项既不下发给模型，也不允许被调用
    tool_specs = resolve_tool_specs(config.disabled_tools)
    switch = _ModelSwitch(config.model, config.fallback_model)
    mode = resolve_initial_mode(config.tool_mode)
    if mode == "json":
        messages[0] = {
            "role": "system",
            "content": _SYSTEM_PROMPT + "\n\n" + _JSON_PROTOCOL_PROMPT.format(
                tools=json.dumps(tool_specs, ensure_ascii=False)
            ),
        }

    deadline = time.monotonic() + config.job_timeout_seconds
    for round_index in range(1, config.max_rounds + 1):
        job.rounds = round_index
        if await _cancel_requested(session, job.id):
            job.status = "cancelled"
            job.current_step = "已按请求终止"
            job.finished_at = _utcnow()
            await steps.add("status", "任务被终止", status="failed")
            await session.commit()
            return
        if time.monotonic() > deadline:
            raise TimeoutError(f"任务超过 {int(config.job_timeout_seconds)} 秒未完成，已中止")

        total, done, filled = _slot_progress(slot_rows)
        progress = 5 + int(85 * done / total) if total else 5
        await steps.progress(f"第 {round_index} 轮 · 已填 {filled}/{total}", progress)

        try:
            if mode == "tools":
                finished = await _run_tools_round(
                    session, messages, runtime, steps, config, switch, tool_specs
                )
            else:
                finished = await _run_json_round(messages, runtime, steps, config, switch)
        except LLMToolsUnsupportedError:
            if config.tool_mode == "tools":
                raise
            await steps.add("status", "当前模型不支持 tools 协议，切换为 JSON 协议继续")
            job.tool_mode = "json"
            mode = "json"
            messages[0] = {
                "role": "system",
                "content": _SYSTEM_PROMPT + "\n\n" + _JSON_PROTOCOL_PROMPT.format(
                    tools=json.dumps(tool_specs, ensure_ascii=False)
                ),
            }
            continue

        job.tool_mode = mode
        if finished:
            break
    else:
        await steps.add("status", f"达到轮次上限 {config.max_rounds}，用已有结果出稿", status="failed")

    await _close_untouched_slots(slot_rows)
    _apply_slot_progress(job, slot_rows)
    job.current_step = "回写 Word 母本"
    job.progress = 92
    await session.commit()

    await _render_and_store(session, job, report, template, slot_rows, steps)

    _apply_slot_progress(job, slot_rows)
    job.status = "completed"
    job.progress = 100
    job.current_step = "已完成"
    job.finished_at = _utcnow()
    await steps.add("status", "任务完成")
    await session.commit()
    logger.info(
        "report-gen job completed",
        extra={"job_id": str(job.id), "slots": total, "filled": filled, "rounds": job.rounds},
    )


async def _record_failure(session: AsyncSession, job: RdReportGenJob, message: str) -> None:
    job.status = "failed"
    job.error_message = _cut(message, 1000)
    job.current_step = "执行失败"
    job.finished_at = _utcnow()
    max_seq = await session.scalar(
        select(RdReportGenStep.seq)
        .where(RdReportGenStep.job_id == job.id)
        .order_by(RdReportGenStep.seq.desc())
        .limit(1)
    )
    session.add(
        RdReportGenStep(
            job_id=job.id,
            seq=int(max_seq or 0) + 1,
            kind="error",
            title=_cut(f"执行失败：{message}", 300),
            result_summary=_cut(message, _MAX_RESULT_CHARS),
            status="failed",
        )
    )
    await session.commit()


async def _config_from_snapshot(job: RdReportGenJob, config: ReportGenConfig) -> ReportGenConfig:
    """按任务快照重建三档绑定。

    快照存的是任务发起时的档位原值，重解析一次即可还原端点与模型；快照全空的是
    本特性上线前的老任务，退回实时配置，不阻塞重跑。
    """
    if not (job.model_config_name or job.structure_model_name or job.fallback_model_name):
        return config
    main, structure, fallback = await resolve_bindings(
        job.model_config_name, job.structure_model_name, job.fallback_model_name
    )
    return replace(config, model=main, structure_model=structure, fallback_model=fallback)


async def run_report_gen(job_id: UUID) -> dict[str, Any]:
    """执行一次生成：解析母本 → Agent 循环 → 回写成稿。由 core.jobs 调度。"""
    config = await load_config()
    async with async_session_factory() as session:
        job = await _load_job(session, job_id)
        if job is None:
            logger.warning("report-gen job not found", extra={"job_id": str(job_id)})
            return {"status": "missing"}
        if job.status not in ("queued", "running"):
            logger.info("report-gen job skipped", extra={"job_id": str(job_id), "status": job.status})
            return {"status": job.status}

        # 以快照为准：任务发起后改配置不影响本任务，页面展示的模型即实际跑的模型
        config = await _config_from_snapshot(job, config)

        try:
            await _execute(session, job, config)
        except Exception as exc:  # noqa: BLE001 - 统一落失败态后再抛给 core.jobs
            logger.exception("report-gen job failed", extra={"job_id": str(job_id)})
            await session.rollback()
            fresh = await _load_job(session, job_id)
            if fresh is not None:
                await _record_failure(session, fresh, str(exc))
            raise

        return {
            "status": job.status,
            "slots": job.slot_total,
            "filled": job.slot_filled,
            "rounds": job.rounds,
        }


__all__ = ["run_report_gen"]
