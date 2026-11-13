"""backfill hazard person uuids by unique name (+ department disambiguation)

Revision ID: 0097_safety_hazard_person_name_backfill
Revises: 0096_safety_hazard_multi_responsible_and_category_dict
Create Date: 2026-11-09

隐患台账人员匹配口径调整为「姓名唯一即直接关联」后，把历史数据里可以唯一解析的人员 UUID
回填落库，使页面标记、列表筛选、整改/复核通知都用同一份数据：

- 系统内同名 1 人 → 直接绑定；
- 同名多人 → 用该条隐患的责任部门消歧（``department in user.department``），恰好 1 人才绑定；
- 查无此人 / 消歧不唯一 → 保持为空，页面继续显示「待确认」，等人工指定。

幂等：只处理仍缺 UUID 的行，重复执行不会改变结果，也不修改 ``updated_at``。
正式 / UAT 部署由 ``migrate`` 容器执行 ``alembic upgrade head`` 自动生效，无需手动跑脚本。

迁移内自带一份冻结的判定逻辑，不 import 业务 service（业务函数演进后历史迁移仍可重放）。
本迁移只写 ``safety.hazard_reports``，只读 ``identity.users``。
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "0097_safety_hazard_person_name_backfill"
down_revision: str = "0096_safety_hazard_multi_responsible_and_category_dict"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

logger = logging.getLogger("alembic.runtime.migration")

# 与 service.hazard_person.split_person_names 保持一致的姓名快照分隔符
_NAME_SEPARATOR_RE = re.compile(r"[,，、;；/]+")
_BATCH_SIZE = 500
_TABLE = "safety.hazard_reports"


def _split_names(raw: Any) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in _NAME_SEPARATOR_RE.split(str(raw)) if part.strip()]


def _load_candidates(conn: sa.Connection) -> dict[str, list[tuple[str, str | None]]]:
    """姓名 → [(用户 UUID, 部门)]，只读 identity.users。"""
    rows = conn.execute(
        sa.text("SELECT id::text, name, department FROM identity.users WHERE is_deleted IS FALSE")
    ).fetchall()
    candidates: dict[str, list[tuple[str, str | None]]] = {}
    for user_id, name, department in rows:
        if not name:
            continue
        candidates.setdefault(str(name).strip(), []).append((user_id, department))
    return candidates


def _resolve_name(
    name: str | None,
    department_hint: str | None,
    candidates: dict[str, list[tuple[str, str | None]]],
) -> str | None:
    """唯一匹配判定（与 service.hazard_person.resolve_person_name 同规则）。"""
    raw = (name or "").strip()
    if not raw:
        return None
    users = candidates.get(raw) or []
    if not users:
        return None
    if len(users) == 1:
        return users[0][0]
    hint = (department_hint or "").strip()
    if not hint:
        return None
    filtered = [user for user in users if user[1] and hint in user[1]]
    if len(filtered) == 1:
        return filtered[0][0]
    return None


def _backfill_discovered_by(conn: sa.Connection, candidates: dict[str, list[tuple[str, str | None]]]) -> int:
    """发现人/审批人：discovered_by 为空但姓名可唯一解析时回填。"""
    updated = 0
    last_id: Any = None
    while True:
        sql = (
            f"SELECT id, discovered_by_name, department FROM {_TABLE} "
            "WHERE is_deleted IS FALSE AND discovered_by IS NULL "
            "AND discovered_by_name IS NOT NULL AND discovered_by_name <> ''"
        )
        params: dict[str, Any] = {"limit": _BATCH_SIZE}
        if last_id is not None:
            sql += " AND id > :last_id"
            params["last_id"] = last_id
        sql += " ORDER BY id LIMIT :limit"
        rows = conn.execute(sa.text(sql), params).fetchall()
        if not rows:
            break
        for row in rows:
            last_id = row[0]
            user_id = _resolve_name(row[1], row[2], candidates)
            if user_id is None:
                continue
            conn.execute(
                sa.text(f"UPDATE {_TABLE} SET discovered_by = CAST(:user_id AS uuid) WHERE id = :row_id"),
                {"user_id": user_id, "row_id": row[0]},
            )
            updated += 1
    return updated


def _backfill_responsible_single(
    conn: sa.Connection, candidates: dict[str, list[tuple[str, str | None]]]
) -> int:
    """整改负责人（旧单人字段）：rectification_responsible_person 为空时回填。"""
    updated = 0
    last_id: Any = None
    while True:
        sql = (
            "SELECT id, rectification_responsible_person_name, department "
            f"FROM {_TABLE} "
            "WHERE is_deleted IS FALSE AND rectification_responsible_person IS NULL "
            "AND rectification_responsible_person_name IS NOT NULL "
            "AND rectification_responsible_person_name <> ''"
        )
        params: dict[str, Any] = {"limit": _BATCH_SIZE}
        if last_id is not None:
            sql += " AND id > :last_id"
            params["last_id"] = last_id
        sql += " ORDER BY id LIMIT :limit"
        rows = conn.execute(sa.text(sql), params).fetchall()
        if not rows:
            break
        for row in rows:
            last_id = row[0]
            user_id = _resolve_name(row[1], row[2], candidates)
            if user_id is None:
                continue
            conn.execute(
                sa.text(
                    f"UPDATE {_TABLE} SET rectification_responsible_person = "
                    "CAST(:user_id AS uuid) WHERE id = :row_id"
                ),
                {"user_id": user_id, "row_id": row[0]},
            )
            updated += 1
    return updated


def _backfill_responsible_multi(
    conn: sa.Connection, candidates: dict[str, list[tuple[str, str | None]]]
) -> int:
    """整改负责人（多选）：ids 为空且所有姓名都能唯一解析时才写入，避免 ids 与 names 错位。"""
    updated = 0
    last_id: Any = None
    while True:
        sql = (
            "SELECT id, rectification_responsible_person_names, department "
            f"FROM {_TABLE} "
            "WHERE is_deleted IS FALSE "
            "AND (rectification_responsible_person_ids IS NULL "
            "OR rectification_responsible_person_ids::jsonb = '[]'::jsonb) "
            "AND rectification_responsible_person_names IS NOT NULL "
            "AND rectification_responsible_person_names <> ''"
        )
        params: dict[str, Any] = {"limit": _BATCH_SIZE}
        if last_id is not None:
            sql += " AND id > :last_id"
            params["last_id"] = last_id
        sql += " ORDER BY id LIMIT :limit"
        rows = conn.execute(sa.text(sql), params).fetchall()
        if not rows:
            break
        for row in rows:
            last_id = row[0]
            names = _split_names(row[1])
            if not names:
                continue
            user_ids: list[str] = []
            for name in names:
                user_id = _resolve_name(name, row[2], candidates)
                if user_id is None:
                    user_ids = []
                    break
                user_ids.append(user_id)
            if not user_ids:
                continue
            conn.execute(
                sa.text(
                    f"UPDATE {_TABLE} SET "
                    "rectification_responsible_person_ids = CAST(:ids AS json), "
                    "rectification_responsible_person = COALESCE("
                    "rectification_responsible_person, CAST(:first_id AS uuid)), "
                    "rectification_responsible_person_name = COALESCE("
                    "NULLIF(rectification_responsible_person_name, ''), :first_name) "
                    "WHERE id = :row_id"
                ),
                {
                    "ids": json.dumps(user_ids),
                    "first_id": user_ids[0],
                    "first_name": names[0][:100],
                    "row_id": row[0],
                },
            )
            updated += 1
    return updated


def upgrade() -> None:
    conn = op.get_bind()
    candidates = _load_candidates(conn)
    discovered = _backfill_discovered_by(conn, candidates)
    responsible_single = _backfill_responsible_single(conn, candidates)
    responsible_multi = _backfill_responsible_multi(conn, candidates)
    logger.info(
        "0097 person backfill: discovered_by=%d responsible_single=%d responsible_multi=%d",
        discovered,
        responsible_single,
        responsible_multi,
    )


def downgrade() -> None:
    # 幂等数据回填不可逆：人员 UUID 由业务写入路径持续维护，回滚结构时无需撤销已绑定的人。
    pass
