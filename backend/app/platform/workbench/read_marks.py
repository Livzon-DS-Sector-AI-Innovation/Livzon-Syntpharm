"""顶栏待办已读：内容指纹、已读判定与写入。

设计取舍：
- 指纹由客户端从 ``/overview`` 带回，服务端不重新聚合取数（一次已读只写一行，避免
  为了拿指纹再跑 4 个数据源）；客户端传旧指纹时只意味着「新状态仍算未读」，偏安全。
- 已读只在 ``(user_id, source, item_id)`` 上保留一条记录，重复标记走 upsert。
"""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable, Sequence

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.workbench.models import WorkbenchTodoRead
from app.platform.workbench.schemas import TodoReadMark
from app.shared.workbench_types import WorkbenchItem

logger = logging.getLogger(__name__)

#: 指纹分隔符；指纹 = 状态 | 当前环节 | 判定依据
_FINGERPRINT_SEPARATOR = "|"

TodoReadKey = tuple[str, str]


def todo_fingerprint(item: WorkbenchItem) -> str:
    """内容指纹：状态 + 当前环节 + 判定依据（待我审批 / 同角色待办）。

    任何一项变化都视为「新提醒」：用户已读的是旧内容，不应替他把新状态也标成已读。
    """
    return _FINGERPRINT_SEPARATOR.join((item.status or "", item.step_label or "", item.match_kind or ""))


def item_key(item: WorkbenchItem) -> TodoReadKey:
    return (item.source, item.id)


def normalize_marks(marks: Iterable[TodoReadMark]) -> list[TodoReadMark]:
    """按 ``(source, item_id)`` 去重（后者覆盖前者），保持首次出现顺序。

    PostgreSQL 的 ``ON CONFLICT`` 不允许同一条语句里出现重复冲突键，
    因此批量标记前必须先去重。
    """
    by_key: dict[TodoReadKey, TodoReadMark] = {}
    for mark in marks:
        by_key[(mark.source, mark.item_id)] = mark
    return list(by_key.values())


def read_key_set(items: Sequence[WorkbenchItem], stored: dict[TodoReadKey, str]) -> set[TodoReadKey]:
    """命中已读的键集合：仅当库里指纹与当前内容指纹完全一致才算已读。"""
    return {item_key(item) for item in items if stored.get(item_key(item)) == todo_fingerprint(item)}


async def load_read_fingerprints(
    db: AsyncSession,
    user_id: uuid.UUID,
    sources: Iterable[str],
) -> dict[TodoReadKey, str]:
    """一次查出该用户在本次涉及的若干数据源下的已读指纹。"""
    source_list = sorted({source for source in sources if source})
    if not source_list:
        return {}

    stmt = select(
        WorkbenchTodoRead.source,
        WorkbenchTodoRead.item_id,
        WorkbenchTodoRead.fingerprint,
    ).where(
        WorkbenchTodoRead.user_id == user_id,
        WorkbenchTodoRead.is_deleted.is_(False),
        WorkbenchTodoRead.source.in_(source_list),
    )
    result = await db.execute(stmt)
    return {(row.source, row.item_id): row.fingerprint for row in result}


async def mark_reads(
    db: AsyncSession,
    user_id: uuid.UUID,
    marks: Iterable[TodoReadMark],
) -> int:
    """批量标记已读（单条即长度为 1），返回实际写入的记录数。

    幂等：同一 ``(user_id, source, item_id)`` 已存在时只更新指纹与时间。
    """
    normalized = normalize_marks(marks)
    if not normalized:
        return 0

    values = [
        {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "source": mark.source,
            "item_id": mark.item_id,
            "fingerprint": mark.fingerprint,
            "created_by": user_id,
            "updated_by": user_id,
        }
        for mark in normalized
    ]
    stmt = pg_insert(WorkbenchTodoRead).values(values)
    stmt = stmt.on_conflict_do_update(
        constraint="uq_workbench_todo_reads_user_item",
        set_={
            "fingerprint": stmt.excluded.fingerprint,
            "read_at": func.now(),
            "updated_at": func.now(),
            "updated_by": user_id,
            "is_deleted": False,
        },
    )

    try:
        await db.execute(stmt)
    except Exception:
        logger.warning(
            "workbench 待办已读写入失败",
            extra={"user_id": str(user_id), "mark_count": len(values), "biz_module": "workbench"},
            exc_info=True,
        )
        raise
    return len(values)
