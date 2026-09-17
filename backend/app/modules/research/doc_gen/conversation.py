"""对话补全：初抽完成后与用户多轮对话，把口述信息写进槽位结果。

**定位与边界**：
- 会话在「解析 + 初抽落库」后由流水线自动创建（首轮盘点卡由规则生成，不调模型）；
- 对话只做「补值」：用户口述 → 模型抽值 → 服务端校验 → upsert ``doc_gen_slot_values``；
- 渲染仍走既有 confirm 链路，会话状态机（active/completed/skipped）不影响任务状态机；
- 用户只能在**已存在的槽位**上补值（key 必须命中初抽落库集合），不能发明新槽位。

**工具协议（JSON 模拟模式）**：内网网关暂不支持 OpenAI tools 字段，先用结构化
JSON 模拟工具调用——模型在回复里声明 ``fills``（相当于 fill_slot 工具入参），
服务端执行写库并校验；将来网关支持原生 tools 后只需替换提示词与解析层。

**主备降级**：主模型（text 配置）重试后仍失败，且运行时配置了
``DOC_GEN_FALLBACK_MODEL``，再用该模型名尝试一次；全部失败则回复固定话术。
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.llm import llm_client
from app.core.llm.exceptions import LLMError
from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.models import DocGenConversation, DocGenMessage, DocGenSlotValue
from app.modules.research.doc_gen.runtime_config import RuntimeConfig, load_runtime_config
from app.modules.research.doc_gen.template_spec import Slot, TemplateSpec

logger = logging.getLogger(__name__)

CONVERSATION_ACTIVE = "active"
CONVERSATION_COMPLETED = "completed"
CONVERSATION_SKIPPED = "skipped"

ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"

# 送入模型的会话历史上限（条数），防止长对话撑爆上下文
HISTORY_LIMIT = 8
# 盘点卡里选填槽位最多列出多少个（必填不限）
OPTIONAL_LIST_LIMIT = 8
# 模型单次调用最多声明的填充项
MAX_FILLS_PER_TURN = 10

# 需要补值的状态集合（对话阶段的目标：把这些槽位变 ok）
_FILLABLE_STATES = frozenset({status.STATUS_PENDING, status.STATUS_FAILED, status.STATUS_CONFLICT})
# 已有值但需人工核对：对话可以再确认一遍，但优先级低于待补
_VERIFY_STATES = frozenset({status.STATUS_NEEDS_VERIFY, status.STATUS_DRAFT})


class ConversationError(Exception):
    """对话业务错误（会话不存在/已结束/任务状态不对），消息直接给用户看。"""


@dataclass(slots=True)
class SlotFill:
    """模型声明的一次槽位填充（相当于 fill_slot 工具的一次调用）。"""

    key: str
    text: str


@dataclass(slots=True)
class TurnOutcome:
    """一轮对话的结果。"""

    assistant_content: str = ""
    fills: list[SlotFill] = field(default_factory=list)
    rejected: list[str] = field(default_factory=list)  # 被拒绝的槽位 key 与原因


# ---------------------------------------------------------------------------
# 盘点卡（规则生成，不调模型）
# ---------------------------------------------------------------------------


def _fillable_slots(spec: TemplateSpec) -> list[Slot]:
    """可对话补值的槽位：跳过元数据槽位与表格（表格去确认页编辑）。"""
    return [slot for slot in spec.slots if not slot.from_meta and slot.kind != "table"]


async def load_slot_rows(session: AsyncSession, job_id: UUID) -> dict[str, DocGenSlotValue]:
    """任务的槽位结果行（key → 行），对话补值和盘点都以它为准。"""
    result = await session.execute(
        select(DocGenSlotValue).where(DocGenSlotValue.job_id == job_id, ~DocGenSlotValue.is_deleted)
    )
    return {row.slot_key: row for row in result.scalars()}


def _bucket_rows(
    spec: TemplateSpec, rows: dict[str, DocGenSlotValue]
) -> tuple[list[Slot], list[Slot], list[Slot]]:
    """按「待补必填 / 待补选填 / 需人工核对」给槽位分组（顺序保持模板声明序）。"""
    missing_required: list[Slot] = []
    missing_optional: list[Slot] = []
    need_review: list[Slot] = []
    for slot in _fillable_slots(spec):
        row = rows.get(slot.key)
        state = row.state if row is not None else status.STATUS_PENDING
        if state in _FILLABLE_STATES or row is None:
            (missing_required if slot.required else missing_optional).append(slot)
        elif state in _VERIFY_STATES:
            need_review.append(slot)
    return missing_required, missing_optional, need_review


def build_checklist(spec: TemplateSpec, rows: dict[str, DocGenSlotValue]) -> str:
    """生成首轮盘点卡（Markdown）：让用户一眼看到还缺什么、怎么补。"""
    missing_required, missing_optional, need_review = _bucket_rows(spec, rows)
    filled = sum(
        1
        for slot in _fillable_slots(spec)
        if (row := rows.get(slot.key)) is not None and row.state == status.STATUS_OK
    )
    lines = [
        "【资料盘点】",
        f"- 已填充：{filled} 项",
        f"- 待补充（必填）：{len(missing_required)} 项",
        f"- 待补充（选填）：{len(missing_optional)} 项",
        f"- 需人工核对：{len(need_review)} 项",
    ]
    if missing_required:
        lines.append("")
        lines.append("**必填项清单**：")
        lines.extend(f"- {slot.label}：{slot.query_hint or '请提供该信息'}" for slot in missing_required)
    if missing_optional:
        shown = missing_optional[:OPTIONAL_LIST_LIMIT]
        lines.append("")
        lines.append("**选填项**（可直接忽略）：")
        lines.extend(f"- {slot.label}" for slot in shown)
        if len(missing_optional) > len(shown):
            lines.append(f"- …等共 {len(missing_optional)} 项")
    if need_review:
        lines.append("")
        lines.append("**以下项已有值但建议核对**：")
        for slot in need_review[:OPTIONAL_LIST_LIMIT]:
            row = rows.get(slot.key)
            current = ((row.text if row else "") or "").strip()[:60]
            lines.append(f"- {slot.label}：{current}")
    lines.append("")
    lines.append("请直接告诉我缺失信息，例如「受理号是 CXHB2400123，申请日期 2026-03-01」。")
    lines.append("完成后点击「完成对话」，或随时说「跳过对话」改用确认页逐项编辑。")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 会话生命周期
# ---------------------------------------------------------------------------


async def get_conversation(session: AsyncSession, job_id: UUID) -> DocGenConversation | None:
    result = await session.execute(
        select(DocGenConversation).where(DocGenConversation.job_id == job_id, ~DocGenConversation.is_deleted)
    )
    return result.scalar_one_or_none()


async def ensure_conversation(
    session: AsyncSession,
    job_id: UUID,
    spec: TemplateSpec,
    rows: dict[str, DocGenSlotValue],
    config: RuntimeConfig | None = None,
) -> DocGenConversation:
    """初抽落库后调用：幂等创建会话并写入首轮盘点卡。

    由流水线在 ``_review_stage`` 挂接；``config`` 供测试注入，
    调用方负责兜底异常（会话是增强能力，不能拖垮任务）。
    """
    existing = await get_conversation(session, job_id)
    if existing is not None:
        return existing
    config = config if config is not None else await load_runtime_config()
    conversation = DocGenConversation(
        job_id=job_id,
        status=CONVERSATION_ACTIVE,
        round_count=0,
        max_rounds=config.chat_max_rounds,
        snapshot=_snapshot(spec, rows),
    )
    session.add(conversation)
    await session.flush()
    session.add(
        DocGenMessage(
            conversation_id=conversation.id,
            role=ROLE_ASSISTANT,
            content=build_checklist(spec, rows),
        )
    )
    logger.info("文档生成会话已创建", extra={"job_id": str(job_id), "module": "research"})
    return conversation


def _snapshot(spec: TemplateSpec, rows: dict[str, DocGenSlotValue]) -> dict[str, Any]:
    """会话创建时的槽位状态快照（排查用）。"""
    missing_required, missing_optional, need_review = _bucket_rows(spec, rows)
    return {
        "missing_required": [slot.key for slot in missing_required],
        "missing_optional": [slot.key for slot in missing_optional],
        "need_review": [slot.key for slot in need_review],
        "filled": sorted(key for key in rows if rows[key].state == status.STATUS_OK),
    }


async def list_messages(session: AsyncSession, conversation_id: UUID) -> list[DocGenMessage]:
    result = await session.execute(
        select(DocGenMessage)
        .where(DocGenMessage.conversation_id == conversation_id, ~DocGenMessage.is_deleted)
        .order_by(DocGenMessage.created_at.asc(), DocGenMessage.id.asc())
    )
    return list(result.scalars())


async def complete_conversation(session: AsyncSession, job_id: UUID) -> DocGenConversation:
    conversation = await _require_active(session, job_id)
    conversation.status = CONVERSATION_COMPLETED
    return conversation


async def skip_conversation(session: AsyncSession, job_id: UUID) -> DocGenConversation:
    """跳过对话：效果与完成相同，但不计入轮数（语义区分供前端展示）。"""
    conversation = await _require_active(session, job_id)
    conversation.status = CONVERSATION_SKIPPED
    return conversation


async def _require_active(session: AsyncSession, job_id: UUID) -> DocGenConversation:
    conversation = await get_conversation(session, job_id)
    if conversation is None:
        raise ConversationError("该任务还没有对话会话（任务可能尚未完成解析）")
    if conversation.status != CONVERSATION_ACTIVE:
        raise ConversationError("对话已结束，请到确认页逐项检查后确认生成")
    return conversation


# ---------------------------------------------------------------------------
# 模型调用与填充校验（JSON 模拟模式的「工具循环」）
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """你是原料药厂研发文档的资料补全助手。用户正在为一份文档补充缺失信息。
规则：
1. 只从用户消息中抽取槽位值，用户没说的不得编造；
2. 值完整且无歧义才放进 fills，含糊的保留追问；
3. 一次回复可以包含多个槽位；
4. answer 用简体中文：先一句确认你理解的值（若有），再追问剩余缺失项（一次最多 3 个问题）；
5. 严格返回 JSON 对象：{"fills": [{"key": "槽位key", "text": "值"}], "answer": "回复"}，无新值时 fills 为 []。"""


def _slot_catalog(spec: TemplateSpec, rows: dict[str, DocGenSlotValue]) -> tuple[str, set[str]]:
    """待补槽位目录（模型只能从中选 key）与允许的 key 集合。"""
    missing_required, missing_optional, _need_review = _bucket_rows(spec, rows)
    lines: list[str] = []
    keys: set[str] = set()
    for slot in missing_required:
        keys.add(slot.key)
        lines.append(f"- key={slot.key} | {slot.label} | 类型 {slot.expects} | 提示：{slot.query_hint or slot.label}")
    for slot in missing_optional[:OPTIONAL_LIST_LIMIT]:
        keys.add(slot.key)
        hint = slot.query_hint or slot.label
        lines.append(f"- key={slot.key} | {slot.label}（选填） | 类型 {slot.expects} | 提示：{hint}")
    return "\n".join(lines) if lines else "（没有可补的槽位）", keys


def _history_messages(messages: list[DocGenMessage]) -> list[dict[str, str]]:
    """最近 N 条会话历史（首条盘点卡通常很长，若被截进窗口则丢弃它）。"""
    recent = messages[-HISTORY_LIMIT:]
    return [{"role": m.role, "content": m.content[:2000]} for m in recent]


def _validate_fills(
    fills: Any, allowed_keys: set[str], spec: TemplateSpec
) -> tuple[list[SlotFill], list[str]]:
    """校验模型声明的填充项：key 合法性、槽位类型、长度截断。"""
    slot_by_key = {slot.key: slot for slot in spec.slots}
    accepted: list[SlotFill] = []
    rejected: list[str] = []
    if not isinstance(fills, list):
        rejected.append("fills 字段不是数组，已忽略")
        return accepted, rejected
    for item in fills[:MAX_FILLS_PER_TURN]:
        if not isinstance(item, dict):
            continue
        key = str(item.get("key") or "").strip()
        text = str(item.get("text") or "").strip()
        if not key or not text:
            continue
        if key not in allowed_keys:
            rejected.append(key)
            continue
        slot = slot_by_key.get(key)
        if slot is None or slot.kind == "table":
            rejected.append(key)
            continue
        if len(text) > slot.max_chars:
            text = text[: slot.max_chars]
        accepted.append(SlotFill(key=key, text=text))
    return accepted, rejected


async def _call_model(
    payload_messages: list[dict[str, Any]], config: RuntimeConfig, llm: Any = None
) -> dict[str, Any]:
    """主模型重试 + 备用模型兜底，全部失败抛 LLMError。``llm`` 供测试注入。"""
    client = llm if llm is not None else llm_client
    attempts = max(1, config.max_attempts)
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            return await client.chat_json(
                payload_messages,
                expected_keys=["fills", "answer"],
                temperature=0.2,
            )
        except LLMError as exc:  # Provider/RateLimit/Output/Config 同源异常
            last_error = exc
            logger.warning("对话补全主模型调用失败", extra={"error": type(exc).__name__})
    fallback = config.fallback_model_name.strip()
    if fallback:
        try:
            return await client.chat_json(
                payload_messages,
                expected_keys=["fills", "answer"],
                temperature=0.2,
                model_override=fallback,
            )
        except LLMError as exc:
            last_error = exc
            logger.warning("对话补全备用模型调用失败", extra={"fallback_model": fallback})
    raise last_error if last_error is not None else LLMError("模型调用失败")


async def send_user_message(
    session: AsyncSession,
    job_id: UUID,
    spec: TemplateSpec,
    content: str,
    config: RuntimeConfig | None = None,
    llm: Any = None,
) -> tuple[DocGenConversation, DocGenMessage]:
    """处理一条用户消息：抽值 → 校验 → 写槽位 → 生成助手回复。

    ``config``/``llm`` 供测试注入；不在此处 commit（由 API 层统一提交）。
    """
    content = content.strip()
    if not content:
        raise ConversationError("消息内容不能为空")
    config = config if config is not None else await load_runtime_config()
    conversation = await _require_active(session, job_id)
    if conversation.round_count >= conversation.max_rounds:
        raise ConversationError("已达对话轮数上限，请点击「完成对话」后到确认页逐项检查")

    rows = await load_slot_rows(session, job_id)
    messages = await list_messages(session, conversation.id)
    catalog, allowed_keys = _slot_catalog(spec, rows)

    user_message = DocGenMessage(conversation_id=conversation.id, role=ROLE_USER, content=content)
    session.add(user_message)

    filled_lines = [f"- {row.slot_key}={row.text}" for row in rows.values() if row.state == status.STATUS_OK]
    filled_block = "\n".join(filled_lines[:40]) if filled_lines else "（暂无）"
    payload_messages: list[dict[str, Any]] = [
        {"role": "system", "content": _SYSTEM_PROMPT},
        {"role": "user", "content": f"【可补槽位目录】\n{catalog}"},
        {"role": "user", "content": f"【已填充槽位（不要重复询问）】\n{filled_block}"},
        *_history_messages(messages),
        {"role": "user", "content": content},
    ]

    try:
        parsed = await _call_model(payload_messages, config, llm=llm)
        fills, rejected = _validate_fills(parsed.get("fills"), allowed_keys, spec)
        answer = str(parsed.get("answer") or "").strip()
    except LLMError:
        logger.warning("对话补全模型不可用，降级为规则回复", extra={"job_id": str(job_id)})
        fills, rejected, answer = [], [], ""

    applied = await _apply_fills(session, job_id, rows, fills)

    conversation.round_count += 1
    assistant_content = _compose_reply(answer, applied, rejected, conversation)
    assistant_message = DocGenMessage(
        conversation_id=conversation.id,
        role=ROLE_ASSISTANT,
        content=assistant_content,
        slot_updates=[{"key": f.key, "text": f.text} for f in applied] or None,
    )
    session.add(assistant_message)
    return conversation, assistant_message


async def _apply_fills(
    session: AsyncSession,
    job_id: UUID,
    rows: dict[str, DocGenSlotValue],
    fills: list[SlotFill],
) -> list[SlotFill]:
    """把校验通过的填充值写入槽位行（用户口述置信度最高，state=ok）。"""
    applied: list[SlotFill] = []
    for fill in fills:
        row = rows.get(fill.key)
        if row is None:
            continue
        row.text = fill.text
        row.state = status.STATUS_OK
        row.reason = "来自对话补充"
        row.confidence = 1.0
        row.evidence = []
        applied.append(fill)
    if applied:
        logger.info(
            "对话补全写入槽位",
            extra={"job_id": str(job_id), "keys": [f.key for f in applied], "module": "research"},
        )
    return applied


def _compose_reply(
    answer: str, applied: list[SlotFill], rejected: list[str], conversation: DocGenConversation
) -> str:
    """助手回复 = LLM 回答 + 写入清单 +（可选）轮数提示。"""
    parts: list[str] = []
    if applied:
        keys_text = "、".join(f.key for f in applied)
        parts.append(f"已记录 {keys_text} 共 {len(applied)} 项。")
    if answer:
        parts.append(answer)
    if not applied and not answer:
        parts.append("这次没有补充到新的信息。请继续告诉我缺失项的值，或点击「完成对话」前往确认页。")
    if rejected:
        parts.append(f"（{len(rejected)} 项无法识别，已忽略）")
    if conversation.round_count >= conversation.max_rounds:
        parts.append("已达对话轮数上限，请点击「完成对话」并到确认页逐项检查。")
    return "\n\n".join(parts)


async def reset_conversation(session: AsyncSession, conversation: DocGenConversation) -> None:
    """重开会话：清空消息、轮数归零（保留状态为 active）。"""
    await session.execute(delete(DocGenMessage).where(DocGenMessage.conversation_id == conversation.id))
    conversation.status = CONVERSATION_ACTIVE
    conversation.round_count = 0
    session.add(
        DocGenMessage(
            conversation_id=conversation.id,
            role=ROLE_ASSISTANT,
            content="会话已重置。请告诉我需要补充的信息，或说「跳过对话」。",
        )
    )


__all__ = [
    "CONVERSATION_ACTIVE",
    "CONVERSATION_COMPLETED",
    "CONVERSATION_SKIPPED",
    "ConversationError",
    "build_checklist",
    "complete_conversation",
    "ensure_conversation",
    "get_conversation",
    "list_messages",
    "load_slot_rows",
    "reset_conversation",
    "send_user_message",
    "skip_conversation",
]
