"""Agent 循环：让模型自主决定「读母本 → 查资料 → 写位置 → 收尾」。

与旧版（填充项识别）最大的区别：**不再预先识别槽位**。母本只解析成「可写位置清单」，
写什么、写在哪由模型在生成时决定；每次写入落一条 ``RdReportGenSlot`` 记录，出稿时按
记录回放（见 ``render.py``）。

两种协议：
- ``tools``：OpenAI 兼容 tool calling，模型直接产出 tool_calls（首选）；
- ``json``：模型每轮输出 ``{"thought","action","action_input"}``（端点不支持 tools 时降级）。

无论走哪种，每一步都写进 ``rd_report_gen_steps``：这是详情页「执行过程」的唯一
数据源，也是事后追溯「这条结论从哪来」的依据。工具失败不抛给上层，只记一条
failed 步骤，让模型自己决定换个位置或换资料。
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
from app.modules.research.report_gen import opinions, versions
from app.modules.research.report_gen.config import ReportGenConfig, load_config
from app.modules.research.report_gen.fills import build_fills
from app.modules.research.report_gen.model_binding import ModelBinding, resolve_binding
from app.modules.research.report_gen.outline import build_outline
from app.modules.research.report_gen.prompts import (
    AGENT_JSON_PROTOCOL_PROMPT,
    AGENT_SYSTEM_PROMPT,
    render_prompt,
    with_human_locked_summary,
    with_instruction,
    with_opinion_digest,
)
from app.modules.research.report_gen.references import build_reference_groups
from app.modules.research.report_gen.render import render_document
from app.modules.research.report_gen.structure import open_document, structure_instruction
from app.modules.research.report_gen.template_access import load_template_bytes
from app.modules.research.report_gen.tools import (
    ReportGenRuntime,
    ToolOutcome,
    execute_tool,
    resolve_tool_specs,
)

logger = logging.getLogger(__name__)

_MAX_ARGS_CHARS = 1000
_MAX_RESULT_CHARS = 2000

# 提示词本体在 prompts.py：库里可整段覆盖（REPORT_GEN_AGENT_PROMPT），这里只留兜底与别名，
# 保持既有引用（prompts_version 指纹、测试）不用改。
_SYSTEM_PROMPT = AGENT_SYSTEM_PROMPT
_JSON_PROTOCOL_PROMPT = AGENT_JSON_PROTOCOL_PROMPT


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
            summary[str(key)] = _cut(json.dumps(value, ensure_ascii=False, default=str), 300)
    return summary


def _utcnow() -> datetime:
    return datetime.now(UTC)


class _StepWriter:
    """执行轨迹写入器：只追加，seq 连续，超上限后只保留状态行。

    轨迹按批落库：``add`` 只 flush，由 ``commit_pending`` 与两个 ``progress`` 在进度上报点
    提交。逐条 commit 会让「一轮 10 次写入」变成 20+ 次事务往返，详情页接上轨迹轮询后
    这个写放大还会被进一步放大；flush 已能保证 seq 连续与行可见（同会话内）。
    """

    def __init__(self, session: AsyncSession, job: RdReportGenJob, max_steps: int) -> None:
        self.session = session
        self.job = job
        self.max_steps = max_steps
        self.seq = 0
        # 节流上报的基线：上次落库的进度值与时刻
        self._last_progress = -1
        self._last_progress_at = 0.0
        # 上次上报时的已写入处数：只有真的写进去了才推进覆盖率与进度条
        self.last_written = 0

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
        await self.session.flush()

    async def commit_pending(self) -> None:
        """把已 flush 的轨迹与业务改动一起提交。"""
        await self.session.commit()

    async def progress(self, current_step: str, progress: int) -> None:
        self.job.current_step = _cut(current_step, 300)
        self.job.progress = max(0, min(progress, 100))
        self._last_progress = self.job.progress
        self._last_progress_at = time.monotonic()
        await self.session.commit()

    async def progress_throttled(
        self,
        current_step: str,
        progress: int,
        *,
        min_delta: int = 2,
        min_interval_seconds: float = 3.0,
    ) -> bool:
        """写工具批内推进进度：增幅够大或间隔够久才落库，返回是否真的上报。

        阈值存在的意义：一次模型回复可能连写 10 处位置，逐处上报既打库又让进度条抖动；
        完全不报则一轮内进度静止（单轮最长可到模型超时的 180 秒）。
        """
        value = max(0, min(progress, 100))
        now = time.monotonic()
        if value - self._last_progress < min_delta and now - self._last_progress_at < min_interval_seconds:
            return False
        self.job.current_step = _cut(current_step, 300)
        self.job.progress = value
        self._last_progress = value
        self._last_progress_at = now
        await self.session.commit()
        return True


async def _load_job(session: AsyncSession, job_id: UUID) -> RdReportGenJob | None:
    result = await session.execute(
        select(RdReportGenJob).where(RdReportGenJob.id == job_id, RdReportGenJob.is_deleted.is_(False))
    )
    return result.scalars().first()


async def _cancel_requested(session: AsyncSession, job_id: UUID) -> bool:
    value = await session.scalar(select(RdReportGenJob.cancel_requested).where(RdReportGenJob.id == job_id))
    return bool(value)


def _apply_coverage(job: RdReportGenJob, coverage: dict[str, Any]) -> None:
    """把覆盖率同步到任务行：''slot_total'' 现在表示「可写位置总数」。"""
    job.slot_total = int(coverage.get("writable_total") or 0)
    job.slot_filled = int(coverage.get("written") or 0)
    job.slot_gap = int(coverage.get("unwritten") or 0)


# 生成期的四个阶段都以「写入资料到文档」这类措辞出现在 current_step 里，
# 前端 types/research/report-gen.ts 的 stageOfJob 按关键词点亮阶段条，改文案要同步那边。
STEP_TEXT_WRITING = "写入资料到文档"
STEP_TEXT_TEMPLATE = "读取 Word 模板"
STEP_TEXT_OPINIONS = "汇总历史评审意见"
STEP_TEXT_RENDERING = "生成 Word 文档"


def _coverage_percent(coverage: dict[str, Any]) -> int:
    """覆盖率 → 进度百分数：5% 起步、90% 封顶，留给「出稿归档」最后一段。"""
    total = max(int(coverage.get("writable_total") or 0), 1)
    return 5 + int(85 * int(coverage.get("written") or 0) / total)


def _writing_step_text(coverage: dict[str, Any]) -> str:
    return f"{STEP_TEXT_WRITING} · 已写 {coverage.get('written', 0)}/{coverage.get('writable_total', 0)} 处"


async def _load_slot_rows(session: AsyncSession, job: RdReportGenJob) -> dict[str, RdReportGenSlot]:
    """取本次任务已有的写入记录（重跑时沿用，按 slot_key 覆盖）。"""
    result = await session.execute(
        select(RdReportGenSlot).where(RdReportGenSlot.job_id == job.id, RdReportGenSlot.is_deleted.is_(False))
    )
    return {row.slot_key: row for row in result.scalars().all()}


def _system_prompt_for(
    config: ReportGenConfig,
    *,
    job: RdReportGenJob,
    project: RdProject,
    report: RdReport,
    template_name: str,
    writable_total: int,
    instruction: str,
) -> str:
    """渲染本次任务的 system prompt：变量填进去，库里覆盖的整段生效。

    变量只做「事实填空」，不给模型额外自由度——漏传的变量会原样留下 ``$name``，
    比静默替换成空串更容易被发现。
    """
    rendered = render_prompt(
        config.agent_prompt,
        {
            "doc_code": job.doc_code or "（未填写）",
            "drug_name": job.drug_name or project.name,
            "max_rounds": config.max_rounds,
            "report_title": report.title,
            "template_name": template_name or "（未指定）",
            "writable_total": writable_total,
        },
    )
    return with_instruction(rendered, instruction)


def _json_system_prompt(system_prompt: str, tool_specs: list[dict[str, Any]]) -> str:
    return system_prompt + "\n\n" + AGENT_JSON_PROTOCOL_PROMPT.format(tools=json.dumps(tool_specs, ensure_ascii=False))


def _build_messages(
    job: RdReportGenJob,
    project: RdProject,
    report: RdReport,
    writable_total: int,
    system_prompt: str,
) -> list[dict[str, Any]]:
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
        f"## 模板\n- 可写位置：{writable_total} 个\n"
        "请开始：先读可写位置总览，再按章节检索资料并批量写入；"
        "全部处理完后整理参考资料并 finalize。"
    )
    return [
        {"role": "system", "content": system_prompt},
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
            f"主模型 {switch.main.display or '默认'} 调用失败，已换用自动补齐模型 {switch.fallback.display}",
            status="failed",
        )
        # 轨迹默认只 flush，「换过模型」这条事实必须立刻落库：兜底再次失败时上层会 rollback，
        # 那时 used_fallback 与这条记录都会丢，事后就无法解释为什么实际用的是备用模型
        await steps.commit_pending()
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
            {
                "role": "user",
                "content": "请继续：要写内容就调用 write_paragraph / write_cell；全部处理完调用 finalize。",
            }
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
        if outcome.ok:
            await _report_write_progress(steps, runtime)
        # 一次工具调用（动作 + 结果两条轨迹）合成一次提交：详情页的生成过程基本实时，
        # 写入次数比原来「每条轨迹一次 commit」少一半
        await steps.commit_pending()
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
    await steps.commit_pending()
    return runtime.finalized


async def _report_write_progress(steps: _StepWriter, runtime: ReportGenRuntime) -> None:
    """真正写进内容之后才推进覆盖率与进度条。

    只在 ``written`` 增加时动作：一轮里可能夹着检索、读模板这类工具，若照抄它们的成功结果
    更新进度，详情页会在「写入资料」阶段显示「已写 0/N 处」，看起来像卡住了。
    覆盖率字段每次写入都刷新（便宜），进度条本身按 ``progress_throttled`` 的阈值节流。
    """
    try:
        coverage = runtime.coverage()
    except Exception:  # noqa: BLE001 - 覆盖率算不出来只影响展示，不影响生成
        logger.warning("report-gen coverage failed", exc_info=True)
        return
    written = int(coverage.get("written") or 0)
    if written <= steps.last_written:
        return
    steps.last_written = written
    _apply_coverage(steps.job, coverage)
    await steps.progress_throttled(_writing_step_text(coverage), _coverage_percent(coverage))


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
    if outcome.ok:
        await _report_write_progress(steps, runtime)
    # 与 tools 协议一致：动作 + 结果一次提交，轨迹在详情页里基本实时可见
    await steps.commit_pending()
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


async def _load_template_bytes(job: RdReportGenJob, template: RdDeliverableTemplate) -> bytes:
    """取母本：优先任务快照（任务发起时固定），缺失时回退模板当前文件。

    实现收敛到 ``template_access``：详情页清单也按同一份母本算位置，两处取法必须一致，
    否则模板换版后「写过的位置」和「列出来的位置」会指向不同段落。
    """
    return load_template_bytes(job, template)


async def _render_and_store(
    session: AsyncSession,
    job: RdReportGenJob,
    report: RdReport,
    template: RdDeliverableTemplate | None,
    slot_rows: dict[str, RdReportGenSlot],
    steps: _StepWriter,
    coverage: dict[str, Any],
) -> None:
    template_bytes = await _load_template_bytes(job, template) if template is not None else b""
    if not template_bytes:
        raise RuntimeError("这次生成没有记录用哪份 Word 模板文件，没法出稿。请回到报告列表点「编辑」重新选模板再生成。")

    meta = {
        "title": report.title,
        "doc_code": job.doc_code,
        "drug_name": job.drug_name,
        "template_name": template.name if template else "",
    }
    output = render_document(template_bytes, build_fills(slot_rows.values()), meta=meta)

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
    await steps.add(
        "status",
        (
            f"文档已生成：已填写 {coverage['written']}/{coverage['writable_total']} 处，"
            f"待填写 {coverage['unwritten']} 处"
            + (f"，追加 {coverage['appended']} 处" if coverage.get("appended") else "")
        ),
        result=(
            f"参考资料 {len(build_reference_groups(slot_rows.values()))} 条来源；"
            f"没找到位置写入的记录：{', '.join(output.unresolved) if output.unresolved else '无'}"
        ),
    )
    # 留一版 ai_draft：后续人工上传/重渲都会新增版本，初稿始终可回溯
    await versions.record_ai_draft(
        session,
        job,
        file_name=job.document_file_name,
        file_size=len(output.document),
    )
    await session.commit()


async def _execute(session: AsyncSession, job: RdReportGenJob, config: ReportGenConfig) -> None:
    report = await session.get(RdReport, job.report_id)
    project = await session.get(RdProject, job.project_id)
    if report is None or project is None:
        raise RuntimeError("找不到这份报告或它所属的项目，可能已经被删除。")

    template = None
    if job.deliverable_template_id:
        template = await session.get(RdDeliverableTemplate, job.deliverable_template_id)
    if template is None:
        raise RuntimeError("这份报告还没有选 Word 模板文件，先点「编辑」选一份再生成。")

    job.status = "running"
    job.started_at = _utcnow()
    job.progress = 2
    job.current_step = STEP_TEXT_TEMPLATE
    await session.commit()

    steps = _StepWriter(session, job, config.max_steps)
    await steps.add("status", "任务开始：读取 Word 模板的可写位置")

    template_bytes = await _load_template_bytes(job, template)
    outline = build_outline(open_document(template_bytes))
    if outline.writable_total == 0:
        raise RuntimeError("这份模板里没有可填写的位置（既没有空段，也没有占位符），没法生成")

    instruction = structure_instruction(template.template_structure)
    await steps.add(
        "status",
        (
            f"模板读取完成：{outline.paragraph_count} 段 + {outline.table_count} 张表，"
            f"可写位置 {outline.writable_total} 个"
        ),
        result=(
            "；".join(f"{item['section']} {item['writable']} 处" for item in outline.section_brief()[:12])
            or "未识别到章节"
        ),
    )

    # 生成前先整理意见库：没有意见就不调模型；汇总失败降级为原文清单，不阻断出稿。
    # 汇总本身是一次独立的模型调用（可能有几十秒），先把阶段推进上去，避免页面停在 2%。
    job.current_step = STEP_TEXT_OPINIONS
    job.progress = 4
    await steps.commit_pending()
    digest_text = ""
    try:
        digest_result = await opinions.build_digest(session, job, config)
    except Exception:  # noqa: BLE001 - 汇总是增益项，失败照常生成
        logger.exception("report-gen opinion digest failed", extra={"job_id": str(job.id)})
        digest_result = None
    if digest_result is not None:
        digest_text = digest_result.digest.digest_text
        note = "（复用相同意见集合的上一份汇总）" if digest_result.reused else ""
        await steps.add(
            "status",
            f"整理历史评审意见 {digest_result.digest.item_count} 条为写作要求{note}",
            result=_cut(digest_text, 300),
        )

    slot_rows = await _load_slot_rows(session, job)
    runtime = ReportGenRuntime(
        session,
        job,
        project,
        outline,
        slot_rows,
        config,
        report_title=report.title,
        instruction=instruction,
    )
    # 先落一次覆盖率：「可填写 N 处」在第一个字符写进去之前就应可知，
    # 否则进度舞台上这几个数字会一直显示 0，看起来像没在干活
    initial_coverage = runtime.coverage()
    _apply_coverage(job, initial_coverage)
    # 从已有覆盖数起算：重跑时带着上一版已写内容，别让第一次检索就误报「已写 N 处」
    steps.last_written = int(initial_coverage.get("written") or 0)
    await steps.commit_pending()
    # 工具清单在任务开始时算一次：禁用项既不下发给模型，也不允许被调用
    tool_specs = resolve_tool_specs(config.disabled_tools)
    system_prompt = _system_prompt_for(
        config,
        job=job,
        project=project,
        report=report,
        template_name=template.name,
        writable_total=outline.writable_total,
        instruction=instruction,
    )
    locked_labels = [
        row.slot_label or key
        for key, row in slot_rows.items()
        if isinstance(row.anchor, dict) and row.anchor.get("human_locked") is True and (row.value or "").strip()
    ]
    if locked_labels:
        # 执行记录里明确写出来：人工确认是「沿用」而不是「重写」，出稿后好核对
        await steps.add(
            "status",
            f"沿用上一版人工确认内容 {len(locked_labels)} 处，本次不再重写",
            result="、".join(locked_labels[:20]),
        )
    system_prompt = with_opinion_digest(system_prompt, digest_text)
    system_prompt = with_human_locked_summary(system_prompt, locked_labels)
    # 可写总数要扣掉人工确认的位置：否则模型会按未扣减的口径去找「还差几处」反复尝试
    messages = _build_messages(job, project, report, max(outline.writable_total - len(locked_labels), 0), system_prompt)
    switch = _ModelSwitch(config.model, config.fallback_model)
    mode = resolve_initial_mode(config.tool_mode)
    if mode == "json":
        messages[0] = {"role": "system", "content": _json_system_prompt(system_prompt, tool_specs)}

    deadline = time.monotonic() + config.job_timeout_seconds
    target_flagged = False
    for round_index in range(1, config.max_rounds + 1):
        job.rounds = round_index
        if await _cancel_requested(session, job.id):
            job.status = "cancelled"
            job.current_step = "已按请求终止"
            job.finished_at = _utcnow()
            await steps.add("status", "任务被终止", status="failed")
            await session.commit()
            return
        elapsed = time.monotonic() - (deadline - config.job_timeout_seconds)
        if time.monotonic() > deadline:
            raise TimeoutError(f"任务超过 {int(config.job_timeout_seconds)} 秒未完成，已中止")
        if not target_flagged and elapsed > config.job_target_seconds:
            target_flagged = True
            logger.warning(
                "report-gen job exceeds target duration",
                extra={"job_id": str(job.id), "elapsed_seconds": int(elapsed)},
            )
            await steps.add(
                "status",
                f"已用时 {int(elapsed)} 秒，超过目标 {int(config.job_target_seconds)} 秒，剩余位置将按已有内容出稿",
                status="failed",
            )

        coverage = runtime.coverage()
        await steps.progress(
            f"{_writing_step_text(coverage)}（第 {round_index} 轮）",
            _coverage_percent(coverage),
        )

        try:
            if mode == "tools":
                finished = await _run_tools_round(session, messages, runtime, steps, config, switch, tool_specs)
            else:
                finished = await _run_json_round(messages, runtime, steps, config, switch)
        except LLMToolsUnsupportedError:
            if config.tool_mode == "tools":
                raise
            await steps.add("status", "当前模型不支持 tools 协议，切换为 JSON 协议继续")
            job.tool_mode = "json"
            mode = "json"
            messages[0] = {"role": "system", "content": _json_system_prompt(system_prompt, tool_specs)}
            continue

        job.tool_mode = mode
        if finished:
            break
    else:
        await steps.add("status", f"达到轮次上限 {config.max_rounds}，用已有结果出稿", status="failed")

    # 参考资料由写入记录确定性生成：模型忘了调用也不会漏，重复调用则幂等
    if config.references_enabled:
        reference = runtime.write_references()
        await steps.add("status", reference.summary, status="ok" if reference.ok else "failed")

    # 出稿前语义复核：内容与格子含义不符的标待核对（finalize 里也调一次，这里兜住
    # 「没走 finalize 就出稿」的路径：轮次上限、被终止）
    mismatches = runtime.semantic_self_check()
    if mismatches:
        await steps.add(
            "status",
            f"自检发现 {len(mismatches)} 处内容与格子含义不符，已标为待核对",
            result="；".join(f"{item['where']}：{item['reason']}" for item in mismatches[:5]),
            status="failed",
        )

    coverage = runtime.coverage()
    _apply_coverage(job, coverage)
    job.current_step = STEP_TEXT_RENDERING
    job.progress = 92
    await session.commit()

    await _render_and_store(session, job, report, template, slot_rows, steps, coverage)

    _apply_coverage(job, coverage)
    job.status = "completed"
    job.progress = 100
    job.current_step = "已完成"
    job.finished_at = _utcnow()
    await steps.add(
        "status",
        f"任务完成：已写 {coverage['written']}/{coverage['writable_total']} 处",
        result=(
            f"待填写 {coverage['unwritten']} 处"
            + (f"，被拒绝 {coverage['rejected']} 次" if coverage.get("rejected") else "")
        ),
    )

    # 若这次生成是从「阶段交付文档」发起的，把 docx 落进该交付文档的附件并回写关联。
    # 内部吞异常：附件复制失败不能让已出稿的任务判成失败，用户仍可从报告详情下载。
    from app.modules.research.deliverable_generation import sync_job_result

    await sync_job_result(session, job)

    await session.commit()
    logger.info(
        "report-gen job completed",
        extra={
            "job_id": str(job.id),
            "slots": coverage["writable_total"],
            "filled": coverage["written"],
            "rounds": job.rounds,
            "elapsed_seconds": int(elapsed),
        },
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
    """按任务快照重建两个档位。

    快照存的是任务发起时的档位原值，重解析一次即可还原端点与模型；快照全空的是
    本特性上线前的老任务，退回实时配置，不阻塞重跑。``structure_model_name`` 是结构
    识别时代的遗留列，这里不读也不用（列本身保留，不建迁移）。
    """
    if not (job.model_config_name or job.fallback_model_name):
        return config
    main = await resolve_binding(job.model_config_name)
    fallback = await resolve_binding(job.fallback_model_name)
    return replace(config, model=main, fallback_model=fallback)


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
