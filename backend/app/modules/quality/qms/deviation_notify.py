"""偏差通知：即时流转卡片与定时扫描共用的飞书发送封装。

约束：

- 通知异步发送（``spawn``），失败只记日志，不影响主事务与接口响应；
- 接收方与开关存 ``core.module_settings``（module=``quality-deviation``，key=``NOTIFY``），
  配置缺失时按「全开 + 无群聊」处理，不会因缺配置阻断流程；
- 日志不输出 open_id / 手机号等敏感标识。
"""

from __future__ import annotations

import json
import logging
from collections.abc import Coroutine, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from app.core.config import get_settings
from app.core.tasks import spawn_task
from app.platform.notification.feishu_client import send_feishu_card
from app.shared.config_reader import get_module_setting

from . import deviation_ledger_constants as constants
from .deviation_flow import HandlerRef

logger = logging.getLogger(__name__)

MODULE = "quality-deviation"
SETTING_KEY = "NOTIFY"
DETAIL_PATH = "/quality/deviation/{ledger_id}"
#: 详情页审批区锚点（``ReviewCard`` 的 ``id="review"``），点开即定位到待审批操作
REVIEW_ANCHOR = "#review"
#: 卡片正文里意见的最大长度（超出截断，避免卡片过长被折叠）
MAX_CONTENT_LENGTH = 120

_EVENT_KEYS = ("flow", "ai_done", "overdue", "weekly", "gmp_group")


@dataclass(frozen=True, slots=True)
class NotifySettings:
    """通知配置。"""

    enabled: bool = True
    chat_id: str = ""
    events: dict[str, bool] = field(default_factory=dict)

    def enabled_for(self, event: str) -> bool:
        if not self.enabled:
            return False
        return bool(self.events.get(event, True))


@dataclass(frozen=True, slots=True)
class LedgerNotice:
    """脱离 ORM 会话的通知快照。"""

    id: str
    code: str
    title: str
    department: str
    status_label: str
    reporter_id: str
    reporter_name: str
    final_code: str | None = None
    level_label: str = "-"
    discovery_date: str = "-"


def to_notice(ledger: Any, *, reporter_name: str = "") -> LedgerNotice:
    """把台账行转成通知快照（只取标量字段，避免会话关闭后触发懒加载）。"""
    raw_date = getattr(ledger, "discovery_date", None)
    if isinstance(raw_date, (date, datetime)):
        discovery_date = raw_date.isoformat()
    else:
        discovery_date = str(raw_date) if raw_date else "-"
    return LedgerNotice(
        id=str(ledger.id),
        code=str(ledger.final_code or ledger.code),
        title=str(ledger.title),
        department=str(ledger.department),
        status_label=constants.status_label(getattr(ledger, "status", None)),
        reporter_id=str(ledger.reporter_id),
        reporter_name=reporter_name or "-",
        final_code=ledger.final_code,
        level_label=constants.level_label(getattr(ledger, "deviation_level", None)),
        discovery_date=discovery_date,
    )


async def load_notify_settings() -> NotifySettings:
    """读取通知配置；JSON 解析失败或字段缺失时按默认值兜底。"""
    raw = await get_module_setting(MODULE, SETTING_KEY, "")
    if not raw:
        return NotifySettings(events={key: True for key in _EVENT_KEYS})
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("deviation notify setting is not json", extra={"app_module": "quality"})
        return NotifySettings(events={key: True for key in _EVENT_KEYS})
    if not isinstance(payload, dict):
        return NotifySettings(events={key: True for key in _EVENT_KEYS})
    events_raw = payload.get("events") or {}
    events = {key: bool(events_raw.get(key, True)) for key in _EVENT_KEYS}
    return NotifySettings(
        enabled=bool(payload.get("enabled", True)),
        chat_id=str(payload.get("chat_id") or ""),
        events=events,
    )


def absolute_url(path: str) -> str:
    """把前端路径拼成绝对地址（飞书卡片按钮）。"""
    base = (get_settings().FRONTEND_URL or "").rstrip("/")
    return f"{base}{path}" if base else path


def detail_url(ledger_id: str, *, anchor: str = REVIEW_ANCHOR) -> str:
    """偏差详情页绝对地址（飞书卡片按钮），默认直接定位到审批区。"""
    return absolute_url(DETAIL_PATH.format(ledger_id=ledger_id)) + (anchor or "")


def spawn(coro: Coroutine[Any, Any, None]) -> None:
    """后台发送通知，异常只记日志（统一走 ``app.core.tasks.spawn_task``）。"""
    spawn_task(coro, name="deviation-notify")


async def _send(
    receive_id: str,
    *,
    title: str,
    content: str,
    url: str | None = None,
    receive_id_type: str = "open_id",
    action_text: str = "去审批",
) -> None:
    actions: list[Any] = []
    if url:
        actions.append({"text": action_text, "url": url})
    await send_feishu_card(
        receive_id=receive_id,
        receive_id_type=receive_id_type,
        title=title,
        content=content,
        actions=actions,
    )


async def send_to_users(
    recipients: Sequence[HandlerRef],
    *,
    title: str,
    content: str,
    url: str | None = None,
    action_text: str = "去审批",
) -> int:
    """逐个发送，返回成功条数。

    飞书标识优先 ``feishu_open_id``（SSO 登录即写入），缺失时回退历史
    ``feishu_user_id``；两者都没有的用户记一条汇总告警（不再静默丢弃），
    便于排查「配置了处理人却收不到通知」。
    """
    sent: set[str] = set()
    skipped: list[str] = []
    delivered = 0
    for ref in recipients:
        receive_id = ref.feishu_id
        if not receive_id:
            skipped.append(str(ref.id))
            continue
        if receive_id in sent:
            continue
        sent.add(receive_id)
        try:
            await _send(
                receive_id,
                title=title,
                content=content,
                url=url,
                receive_id_type=ref.feishu_id_type,
                action_text=action_text,
            )
            delivered += 1
        except Exception:  # noqa: BLE001 - 单个接收方失败不影响其余人
            logger.warning(
                "deviation notification to user failed",
                extra={"app_module": "quality", "user_id": str(ref.id)},
                exc_info=True,
            )
    if skipped:
        logger.warning(
            "deviation notification skipped: recipients without feishu id",
            extra={"app_module": "quality", "user_ids": skipped, "title": title},
        )
    return delivered


async def send_to_chat(chat_id: str, *, title: str, content: str, url: str | None = None) -> None:
    """向群聊发送卡片。"""
    if not chat_id:
        return
    await _send(chat_id, title=title, content=content, url=url, receive_id_type="chat_id")


async def send_test_card(ref: HandlerRef, *, operator_name: str = "") -> None:
    """给指定用户发一张测试卡片（配置页自检用），失败直接抛给调用方。"""
    receive_id = ref.feishu_id
    if not receive_id:
        raise ValueError("该账号未绑定飞书标识")
    content = "\n".join(
        [
            "**偏差流转通知 · 链路自检**",
            f"接收人：{operator_name or ref.name}",
            "收到本消息说明：平台飞书应用凭证可用、你的账号已绑定飞书 open_id。",
            "后续偏差流转到你的环节时，会收到带「去审批」按钮的卡片。",
        ]
    )
    await _send(
        receive_id,
        title="偏差通知测试",
        content=content,
        url=absolute_url("/quality/deviation"),
        receive_id_type=ref.feishu_id_type,
        action_text="打开偏差台账",
    )


def _clip(text: str, limit: int = MAX_CONTENT_LENGTH) -> str:
    """压缩空白并截断，避免卡片正文过长。"""
    cleaned = " ".join((text or "").split())
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1] + "…"


def _format_elapsed(hours: float | None) -> str:
    """上一环节停留时长的可读表示（<1 天用小时）。"""
    if not hours or hours <= 0:
        return ""
    if hours < 24:
        return f"{hours:.0f} 小时"
    return f"{hours / 24:.1f} 天"


def _transition_title(*, step_label: str, result: str, next_status_label: str) -> str:
    if result == "rejected":
        return f"偏差被退回（{step_label}）"
    if result == "resubmitted":
        return f"偏差已重新提交，待审批：{next_status_label}"
    if step_label == "AI 智能分析":
        return "AI 分析已完成，请开展偏差调查"
    return f"待你处理：{next_status_label}"


def build_transition_summary(
    notice: LedgerNotice,
    *,
    step_label: str,
    result: str,
    content: str,
    actor_name: str,
    next_status_label: str,
    next_role_label: str = "",
    elapsed_hours: float | None = None,
    deadline_days: int | None = None,
) -> str:
    """审批信息摘要（lark_md）：编号/标题、级别/发现日期、部门/上报人、待办环节、上一步、意见。"""
    lines = [
        f"**{notice.code}** {notice.title}",
        f"偏差级别：{notice.level_label}｜发现日期：{notice.discovery_date}",
        f"部门：{notice.department}｜上报人：{notice.reporter_name}",
    ]
    if result == "rejected":
        lines.append(f"退回环节：{step_label}")
        lines.append(f"当前状态：待{next_role_label or '上报人'}修改后重新提交")
    else:
        current = f"当前环节：{next_status_label}"
        if next_role_label:
            current += f"（待{next_role_label}处理）"
        lines.append(current)
    previous = f"上一步：{step_label}｜{actor_name}"
    elapsed = _format_elapsed(elapsed_hours)
    if elapsed:
        previous += f"｜耗时 {elapsed}"
    lines.append(previous)
    if result != "rejected" and deadline_days:
        lines.append(f"处理时限：{deadline_days} 天，超期将在看板标红")
    opinion = _clip(content)
    if opinion:
        lines.append(f"{'退回理由' if result == 'rejected' else '审核意见'}：{opinion}")
    return "\n".join(lines)


async def notify_transition(
    notice: LedgerNotice,
    *,
    step_label: str,
    result: str,
    content: str,
    actor_name: str,
    next_status_label: str,
    recipients: Sequence[HandlerRef],
    reporter: HandlerRef | None = None,
    cross_recipients: Sequence[HandlerRef] = (),
    next_role_label: str = "",
    elapsed_hours: float | None = None,
    deadline_days: int | None = None,
) -> None:
    """流转即时通知：通过 → 下一环节处理人；退回 → 上报人 + 调查人。"""
    config = await load_notify_settings()
    ai_done = result == "approved" and step_label == "AI 智能分析"
    if ai_done and not config.enabled_for("ai_done"):
        return
    if not ai_done and not config.enabled_for("flow"):
        return

    url = detail_url(notice.id)
    body = build_transition_summary(
        notice,
        step_label=step_label,
        result=result,
        content=content,
        actor_name=actor_name,
        next_status_label=next_status_label,
        next_role_label=next_role_label,
        elapsed_hours=elapsed_hours,
        deadline_days=deadline_days,
    )
    title = _transition_title(step_label=step_label, result=result, next_status_label=next_status_label)

    if result == "rejected":
        target = list(recipients)
        if reporter is not None and all(ref.id != reporter.id for ref in target):
            target.append(reporter)
        await send_to_users(target, title=title, content=body, url=url, action_text="去处理")
        return

    await send_to_users(recipients, title=title, content=body, url=url)

    if cross_recipients:
        await send_to_users(
            cross_recipients,
            title="跨部门偏差调查指派",
            content=body + "\n请协助完成跨部门调查。",
            url=url,
            action_text="去处理",
        )


async def notify_closed(
    notice: LedgerNotice,
    *,
    actor_name: str,
    recipients: Sequence[HandlerRef],
) -> None:
    """关闭通知：上报人 + 调查人 + 群聊。"""
    config = await load_notify_settings()
    if not config.enabled_for("flow"):
        return
    body = (
        f"**{notice.code}** {notice.title}\n"
        f"部门：{notice.department}｜上报人：{notice.reporter_name}\n"
        f"偏差级别：{notice.level_label}\n"
        f"最终编号：{notice.final_code or '-'}\n"
        f"操作人：{actor_name}"
    )
    url = detail_url(notice.id)
    await send_to_users(recipients, title="偏差已关闭", content=body, url=url, action_text="查看详情")
    await send_to_chat(config.chat_id, title="偏差已关闭", content=body, url=url)


async def broadcast_to_group(title: str, content: str, *, url: str | None = None) -> None:
    """向配置的群聊发送（定时扫描使用）。"""
    config = await load_notify_settings()
    await send_to_chat(config.chat_id, title=title, content=content, url=url)


__all__ = [
    "DETAIL_PATH",
    "MAX_CONTENT_LENGTH",
    "MODULE",
    "REVIEW_ANCHOR",
    "SETTING_KEY",
    "LedgerNotice",
    "NotifySettings",
    "absolute_url",
    "broadcast_to_group",
    "build_transition_summary",
    "detail_url",
    "load_notify_settings",
    "notify_closed",
    "notify_transition",
    "send_test_card",
    "send_to_chat",
    "send_to_users",
    "spawn",
    "to_notice",
]
