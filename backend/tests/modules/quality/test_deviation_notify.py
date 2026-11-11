"""偏差流转飞书通知：接收人标识解析与卡片内容（不依赖真实飞书与数据库）。

历史问题：接收人只读 ``identity.users.feishu_user_id``（该字段长期为空，
真实 open_id 在 ``feishu_open_id``），且为空时静默跳过，导致流转通知一条也发不出去。
这些用例锁住修复后的行为：open_id 优先、user_id 回退、缺失时告警、链接直达审批区。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

import pytest

from app.modules.quality.qms import deviation_notify as notify
from app.modules.quality.qms.deviation_flow import HandlerDirectory, HandlerRef
from app.modules.quality.qms.deviation_notify import (
    LedgerNotice,
    NotifySettings,
    build_transition_summary,
    detail_url,
    send_to_users,
)


def _ref(
    name: str = "张三",
    *,
    open_id: str | None = None,
    user_id: str | None = None,
) -> HandlerRef:
    return HandlerRef(id=uuid.uuid4(), name=name, feishu_open_id=open_id, feishu_user_id=user_id)


def _notice() -> LedgerNotice:
    return LedgerNotice(
        id="11111111-1111-1111-1111-111111111111",
        code="PC20261111001",
        title="压片机温度超标",
        department="101车间",
        status_label="部门负责人审核",
        reporter_id=str(uuid.uuid4()),
        reporter_name="李四",
        level_label="中等",
        discovery_date="2026-11-10",
    )


class _Capture:
    """记录 send_feishu_card 的调用参数。"""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


# ── 接收人标识解析 ──────────────────────────────────────────────────────


def test_handler_ref_prefers_open_id() -> None:
    """同时有 open_id 与 user_id 时优先用 open_id（SSO 登录即写入，最可靠）。"""
    ref = _ref(open_id="ou_abc", user_id="u123")

    assert ref.feishu_id == "ou_abc"
    assert ref.feishu_id_type == "open_id"


def test_handler_ref_falls_back_to_user_id() -> None:
    """只有历史 user_id 时按 user_id 类型发送，不能直接丢弃。"""
    ref = _ref(user_id="u123")

    assert ref.feishu_id == "u123"
    assert ref.feishu_id_type == "user_id"


def test_directory_resolves_open_id_token() -> None:
    """部门联系人里存的是 open_id 时，也要能反查出人员。"""
    ref = _ref("王五", open_id="ou_xyz")
    directory = HandlerDirectory({ref.id: ref})

    assert directory.resolve(["ou_xyz"]) == [ref.id]
    assert directory.ref(ref.id) is ref


# ── 卡片链接与摘要 ──────────────────────────────────────────────────────


def test_detail_url_points_to_review_section() -> None:
    """按钮直接落在审批区锚点，点开即可操作。"""
    url = detail_url("abc")

    assert url.endswith("/quality/deviation/abc#review")


def test_summary_carries_approval_context() -> None:
    """摘要要让审批人不点进去也能判断轻重缓急。"""
    summary = build_transition_summary(
        _notice(),
        step_label="调查提交",
        result="approved",
        content="已排查为冷却水温度波动",
        actor_name="李四",
        next_status_label="部门负责人审核",
        next_role_label="部门负责人",
        elapsed_hours=30.0,
        deadline_days=3,
    )

    assert "PC20261111001" in summary
    assert "压片机温度超标" in summary
    assert "偏差级别：中等｜发现日期：2026-11-10" in summary
    assert "部门：101车间｜上报人：李四" in summary
    assert "当前环节：部门负责人审核（待部门负责人处理）" in summary
    assert "上一步：调查提交｜李四｜耗时 1.2 天" in summary
    assert "处理时限：3 天" in summary
    assert "审核意见：已排查为冷却水温度波动" in summary


def test_rejected_summary_shows_return_reason() -> None:
    """退回卡片必须展示退回理由与重新提交人，否则处理人无从下手。"""
    summary = build_transition_summary(
        _notice(),
        step_label="部门负责人审核",
        result="rejected",
        content="调查结论缺少根因分析",
        actor_name="赵六",
        next_status_label="已退回",
        next_role_label="上报人/调查人",
        elapsed_hours=2.0,
    )

    assert "退回环节：部门负责人审核" in summary
    assert "当前状态：待上报人/调查人修改后重新提交" in summary
    assert "退回理由：调查结论缺少根因分析" in summary
    assert "处理时限" not in summary


# ── 发送行为 ────────────────────────────────────────────────────────────


async def test_send_to_users_uses_matching_receive_id_type(monkeypatch: pytest.MonkeyPatch) -> None:
    """逐人按标识来源选择 open_id / user_id，并跳过重复接收人。"""
    capture = _Capture()
    monkeypatch.setattr(notify, "send_feishu_card", capture)

    open_ref = _ref("甲", open_id="ou_a")
    legacy_ref = _ref("乙", user_id="u_b")
    unbound_ref = _ref("丙")

    delivered = await send_to_users(
        [open_ref, legacy_ref, unbound_ref, open_ref],
        title="待你处理",
        content="正文",
        url="http://testserver/quality/deviation/x#review",
    )

    assert delivered == 2
    assert [(call["receive_id"], call["receive_id_type"]) for call in capture.calls] == [
        ("ou_a", "open_id"),
        ("u_b", "user_id"),
    ]
    assert capture.calls[0]["actions"][0]["text"] == "去审批"


async def test_send_to_users_warns_when_recipient_has_no_feishu_id(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """没有飞书标识时不再静默：留一条汇总告警，便于排查「配置了人却收不到」。"""
    capture = _Capture()
    monkeypatch.setattr(notify, "send_feishu_card", capture)
    unbound = _ref("丙")

    with caplog.at_level(logging.WARNING, logger=notify.__name__):
        delivered = await send_to_users([unbound], title="待你处理", content="正文")

    assert delivered == 0
    assert capture.calls == []
    assert "recipients without feishu id" in caplog.text
    assert "ou_" not in caplog.text


async def test_notify_transition_sends_reject_notice_to_reporter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """退回：处理人与上报人都要收到，且正文带退回理由。"""
    capture = _Capture()
    monkeypatch.setattr(notify, "send_feishu_card", capture)

    async def _settings() -> NotifySettings:
        return NotifySettings(enabled=True, events={"flow": True, "ai_done": True})

    monkeypatch.setattr(notify, "load_notify_settings", _settings)

    handler = _ref("审核人", open_id="ou_handler")
    reporter = _ref("上报人", open_id="ou_reporter")

    await notify.notify_transition(
        _notice(),
        step_label="部门负责人审核",
        result="rejected",
        content="缺少根因分析",
        actor_name="审核人",
        next_status_label="已退回",
        recipients=[handler],
        reporter=reporter,
        next_role_label="上报人/调查人",
    )

    assert {call["receive_id"] for call in capture.calls} == {"ou_handler", "ou_reporter"}
    for call in capture.calls:
        assert "退回理由：缺少根因分析" in call["content"]
        assert call["title"].startswith("偏差被退回")


async def test_notify_transition_skips_when_flow_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    """关闭「流转即时通知」后不再发送。"""
    capture = _Capture()
    monkeypatch.setattr(notify, "send_feishu_card", capture)

    async def _settings() -> NotifySettings:
        return NotifySettings(enabled=True, events={"flow": False, "ai_done": True})

    monkeypatch.setattr(notify, "load_notify_settings", _settings)

    await notify.notify_transition(
        _notice(),
        step_label="部门负责人审核",
        result="approved",
        content="同意",
        actor_name="审核人",
        next_status_label="所属QA审核",
        recipients=[_ref("QA", open_id="ou_qa")],
    )

    assert capture.calls == []
