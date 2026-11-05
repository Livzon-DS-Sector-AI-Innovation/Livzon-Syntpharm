"""AI 交互日志列表不返回软删除记录。

`AGENTS.md` 规定删除默认软删除，`AiLogService.get_by_id` 一直滤 `is_deleted`；
但 2026-10 新增的 `GET /api/v1/quality/ai/logs` 背后的 `list_logs` 原先只拼业务条件，
软删除日志（含 system_prompt / user_input 原文）会被列表列出、详情却返回 404，
列表与详情口径不一致。这里锁住列表口径，防止以后又退回不带软删除过滤的写法。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.ai.models import QmsAiLog
from app.modules.quality.ai.service import AiLogService


async def test_list_logs_excludes_soft_deleted(db_session: AsyncSession) -> None:
    """软删除的日志不出现在列表里，且 total 与列表同口径。"""
    marker = f"软删除测试-{uuid.uuid4().hex[:8]}"
    now = datetime.now()

    live = QmsAiLog(
        operate_type=marker,
        operator="tester",
        system_prompt="prompt",
        user_input="input",
        created_at=now,
    )
    deleted = QmsAiLog(
        operate_type=marker,
        operator="tester",
        system_prompt="prompt",
        user_input="input",
        created_at=now,
        is_deleted=True,
    )
    db_session.add_all([live, deleted])
    await db_session.flush()

    service = AiLogService(db_session)
    logs, total = await service.list_logs(operate_type=marker, page=1, page_size=50)

    # operate_type 用随机标记圈定数据，断言不受库内其他日志影响
    assert total == 1
    assert [log.id for log in logs] == [live.id]

    # 与 get_by_id 口径一致：软删除的查不到
    assert await service.get_by_id(deleted.id) is None
    assert await service.get_by_id(live.id) is not None
