"""对话补全测试（假模型 + 假 session，不打真实服务/数据库）。

槽位 key 从模板动态选取，避免与模板内容耦合。
"""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.llm.exceptions import LLMProviderError
from app.modules.research.doc_gen import conversation as conversation_mod
from app.modules.research.doc_gen import status
from app.modules.research.doc_gen.conversation import (
    ConversationError,
    SlotFill,
    _validate_fills,
    build_checklist,
    complete_conversation,
    ensure_conversation,
    send_user_message,
)
from app.modules.research.doc_gen.models import DocGenConversation, DocGenMessage, DocGenSlotValue
from app.modules.research.doc_gen.runtime_config import RuntimeConfig
from app.modules.research.doc_gen.templates import get_template_spec


class FakeLLM:
    """返回预设响应、记录调用次数，可配置失败。"""

    def __init__(self, response: dict[str, Any] | Exception) -> None:
        self._response = response
        self.calls = 0

    async def chat_json(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        self.calls += 1
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


class FakeResult:
    """模拟 session.execute 结果：scalar_one_or_none 与 scalars 迭代。"""

    def __init__(self, items: list[Any]) -> None:
        self._items = items

    def scalars(self) -> FakeResult:
        return self

    def scalar_one_or_none(self) -> Any:
        return self._items[0] if self._items else None

    def all(self) -> list[Any]:
        return self._items

    def __iter__(self):  # noqa: D105
        return iter(self._items)


class FakeSession:
    """按查询实体分发的假 session（conversation 模块三种查询）。"""

    def __init__(
        self,
        conversation: DocGenConversation | None,
        rows: dict[str, DocGenSlotValue],
        messages: list[DocGenMessage],
    ) -> None:
        self.conversation = conversation
        self.rows = rows
        self.messages = messages
        self.added: list[Any] = []
        self.flushed = 0

    async def execute(self, stmt: Any) -> FakeResult:
        entity = stmt.column_descriptions[0]["entity"]
        if entity is DocGenConversation:
            return FakeResult([self.conversation] if self.conversation else [])
        if entity is DocGenMessage:
            return FakeResult(list(self.messages))
        if entity is DocGenSlotValue:
            return FakeResult(list(self.rows.values()))
        raise AssertionError(f"unexpected query: {entity}")

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushed += 1


def _spec() -> Any:
    return get_template_spec("tech_research_report").model_copy(deep=True)


def _row(job_id: Any, key: str, text: str, state: str) -> DocGenSlotValue:
    return DocGenSlotValue(
        job_id=job_id,
        slot_key=key,
        text=text,
        state=state,
        confidence=0.5 if state != status.STATUS_OK else 0.95,
        evidence=[],
        reason="初抽",
    )


def _pick(spec: Any, predicate: Any) -> Any:
    """按谓词挑可对话补值的槽位（非 meta、非表格）。"""
    candidates = [s for s in spec.slots if not s.from_meta and s.kind != "table" and predicate(s)]
    assert candidates, "模板应存在满足条件的可补槽位"
    return candidates[0]


def _rows(spec: Any, job_id: Any) -> dict[str, DocGenSlotValue]:
    """一组测试行：前三个可补槽位分别置 OK / CONFLICT / NEEDS_VERIFY。"""
    fillable = [s for s in spec.slots if not s.from_meta and s.kind != "table"]
    assert len(fillable) >= 3, "模板应至少有 3 个可对话补值槽位"
    ok_slot, conflict_slot, verify_slot = fillable[0], fillable[1], fillable[2]
    return {
        ok_slot.key: _row(job_id, ok_slot.key, "某品种", status.STATUS_OK),
        conflict_slot.key: _row(job_id, conflict_slot.key, status.CONFLICT_MARK, status.STATUS_CONFLICT),
        verify_slot.key: _row(job_id, verify_slot.key, "待核对的值", status.STATUS_NEEDS_VERIFY),
    }


def _conversation(max_rounds: int = 3, round_count: int = 0) -> DocGenConversation:
    return DocGenConversation(
        job_id=uuid4(), status=conversation_mod.CONVERSATION_ACTIVE, round_count=round_count, max_rounds=max_rounds
    )


def _config(max_attempts: int = 1) -> RuntimeConfig:
    return RuntimeConfig(max_attempts=max_attempts, chat_max_rounds=3, fallback_model_name="")


# ---------------------------------------------------------------------------
# 盘点卡与 fills 校验（纯函数）
# ---------------------------------------------------------------------------


async def test_checklist_buckets_pending_and_review() -> None:
    """盘点卡：CONFLICT/无行槽位归待补，NEEDS_VERIFY 归核对，已填不列。"""
    spec = _spec()
    job_id = uuid4()
    rows = _rows(spec, job_id)
    ok_key, verify_key = next(k for k, v in rows.items() if v.state == status.STATUS_OK), next(
        k for k, v in rows.items() if v.state == status.STATUS_NEEDS_VERIFY
    )
    conflict_key = next(k for k, v in rows.items() if v.state == status.STATUS_CONFLICT)
    label = {s.key: s.label for s in spec.slots}
    card = build_checklist(spec, rows)
    assert "已填充：1 项" in card
    assert label[conflict_key] in card  # CONFLICT 槽位在待补清单里
    assert label[verify_key] in card  # NEEDS_VERIFY 槽位在核对清单里
    assert label[ok_key] not in card  # 已填槽位不进任何清单


async def test_validate_fills_rejects_unknown_key() -> None:
    """非法 key（不在允许集合）被拒绝，合法项通过并截断超长文本。"""
    spec = _spec()
    slot = _pick(spec, lambda s: True)
    fills, rejected = _validate_fills(
        [
            {"key": slot.key, "text": "合法值"},
            {"key": "invented_slot_xxx", "text": "x"},
            {"key": slot.key, "text": "y" * (slot.max_chars + 10)},
            "bad-item",
        ],
        {slot.key},
        spec,
    )
    assert rejected == ["invented_slot_xxx"]
    assert len(fills) == 2
    assert len(fills[1].text) == slot.max_chars


# ---------------------------------------------------------------------------
# send_user_message（fake session + fake llm）
# ---------------------------------------------------------------------------


async def test_send_message_applies_fills() -> None:
    """模型返回合法 fills → 写入槽位行（state=ok），助手回复含确认与追问。"""
    spec = _spec()
    conv = _conversation()
    rows = _rows(spec, conv.job_id)
    target_key = next(k for k, v in rows.items() if v.state == status.STATUS_CONFLICT)
    session = FakeSession(conv, rows, messages=[])
    llm = FakeLLM({"fills": [{"key": target_key, "text": "CXHB2400123"}], "answer": "已记录，请问申请日期？"})
    _, assistant = await send_user_message(
        session, conv.job_id, spec, f"{target_key} 是 CXHB2400123", config=_config(), llm=llm
    )
    assert llm.calls == 1
    assert rows[target_key].text == "CXHB2400123"
    assert rows[target_key].state == status.STATUS_OK
    assert rows[target_key].confidence == 1.0
    assert rows[target_key].reason == "来自对话补充"
    assert conv.round_count == 1
    assert target_key in (assistant.content or "")
    assert assistant.slot_updates is not None and assistant.slot_updates[0]["key"] == target_key


async def test_send_message_rejects_invented_key() -> None:
    """模型编造的槽位不写入，回复提示无法识别。"""
    spec = _spec()
    conv = _conversation()
    rows = _rows(spec, conv.job_id)
    session = FakeSession(conv, rows, messages=[])
    llm = FakeLLM({"fills": [{"key": "made_up_xxx", "text": "x"}], "answer": "好的"})
    _, assistant = await send_user_message(session, conv.job_id, spec, "随便说点什么", config=_config(), llm=llm)
    assert "made_up_xxx" not in rows  # 没有发明新槽位行
    assert [row.text for row in rows.values()] == ["某品种", status.CONFLICT_MARK, "待核对的值"]  # 值全部未被改写
    assert "无法识别" in (assistant.content or "")
    assert assistant.slot_updates is None


async def test_send_message_degrades_when_model_down() -> None:
    """模型不可用 → 规则回复，不抛异常，槽位未被写入。"""
    spec = _spec()
    conv = _conversation()
    rows = _rows(spec, conv.job_id)
    target_key = next(k for k, v in rows.items() if v.state == status.STATUS_CONFLICT)
    original_text = rows[target_key].text
    session = FakeSession(conv, rows, messages=[])
    llm = FakeLLM(LLMProviderError("网关不可用"))
    _, assistant = await send_user_message(session, conv.job_id, spec, "补充信息", config=_config(), llm=llm)
    assert llm.calls == 1
    assert rows[target_key].text == original_text  # 未被写入
    assert "没有补充到新的信息" in (assistant.content or "")


async def test_send_message_fallback_model_used() -> None:
    """主模型失败 → 使用备用模型名重试成功。"""
    spec = _spec()
    conv = _conversation()
    rows = _rows(spec, conv.job_id)
    session = FakeSession(conv, rows, messages=[])

    class FallbackLLM:
        def __init__(self) -> None:
            self.seen_models: list[str | None] = []

        async def chat_json(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
            self.seen_models.append(kwargs.get("model_override"))
            if kwargs.get("model_override") == "qwen-backup":
                return {"fills": [], "answer": "备用模型在线"}
            raise LLMProviderError("主模型挂了")

    llm = FallbackLLM()
    config = RuntimeConfig(max_attempts=1, chat_max_rounds=3, fallback_model_name="qwen-backup")
    _, assistant = await send_user_message(session, conv.job_id, spec, "补充信息", config=config, llm=llm)
    assert llm.seen_models == [None, "qwen-backup"]
    assert "备用模型在线" in (assistant.content or "")


async def test_send_message_round_limit() -> None:
    """轮数用尽后拒绝继续对话。"""
    spec = _spec()
    conv = _conversation(round_count=3, max_rounds=3)
    session = FakeSession(conv, _rows(spec, conv.job_id), messages=[])
    try:
        await send_user_message(
            session, conv.job_id, spec, "继续", config=_config(), llm=FakeLLM({"fills": [], "answer": ""})
        )
    except ConversationError as exc:
        assert "轮数上限" in str(exc)
    else:
        raise AssertionError("应抛 ConversationError")


# ---------------------------------------------------------------------------
# 会话生命周期
# ---------------------------------------------------------------------------


async def test_ensure_conversation_creates_checklist_once() -> None:
    """首建写入盘点卡消息；已存在会话时幂等返回。"""
    spec = _spec()
    rows = _rows(spec, uuid4())
    session = FakeSession(None, rows, messages=[])
    conv = await ensure_conversation(session, uuid4(), spec, rows, config=_config())
    assert session.flushed == 1
    cards = [o for o in session.added if isinstance(o, DocGenMessage)]
    assert len(cards) == 1 and cards[0].content.startswith("【资料盘点】")
    # 幂等：会话已存在则不再生成
    session2 = FakeSession(conv, rows, messages=[])
    again = await ensure_conversation(session2, conv.job_id, spec, rows, config=_config())
    assert again is conv
    assert session2.flushed == 0


async def test_complete_conversation_sets_status() -> None:
    """完成对话：状态置 completed，已补值不受影响。"""
    spec = _spec()
    conv = _conversation()
    session = FakeSession(conv, _rows(spec, conv.job_id), messages=[])
    result = await complete_conversation(session, conv.job_id)
    assert result.status == conversation_mod.CONVERSATION_COMPLETED


def test_slot_fill_dataclass() -> None:
    """SlotFill 数据类基本属性。"""
    fill = SlotFill(key="k", text="v")
    assert fill.key == "k" and fill.text == "v"
