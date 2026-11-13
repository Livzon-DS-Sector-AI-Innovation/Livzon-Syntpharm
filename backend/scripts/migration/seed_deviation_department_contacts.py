"""把旧偏差配置（QA / 负责人）幂等初始化到 ``quality.department_contacts``。

背景：新偏差审核流的处理人唯一来源是部门联系人表。旧台账的 QA 与负责人配置分别存在
``qms.qms_deviation_qa_config`` 与 ``qms.qms_deviation_leader_config``，上线前需要搬过来，
否则新流程会因解析不到处理人而自动跳过环节。

幂等约束：

- 已存在的部门只补空缺字段，不覆盖人工维护过的值；
- 人员 token（飞书 open_id）已在数组中则跳过；
- 能对上 ``identity.users.feishu_user_id`` 的负责人写入 ``dept_head_id``，对不上的放进
  ``additional_contacts``（保留信息，不阻断脚本）。

用法：

    uv run python scripts/migration/seed_deviation_department_contacts.py
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402
from app.modules.quality.qms.deviation_department_models import DepartmentContact  # noqa: E402

_LEADERS_SQL = text(
    "SELECT open_id, name, department FROM qms.qms_deviation_leader_config "
    "WHERE is_deleted = FALSE AND is_active = TRUE ORDER BY created_at"
)
_QA_SQL = text(
    "SELECT open_id, name, department FROM qms.qms_deviation_qa_config "
    "WHERE is_deleted = FALSE AND is_active = TRUE ORDER BY created_at"
)
_USER_BY_FEISHU_SQL = text("SELECT id FROM identity.users WHERE feishu_user_id = :open_id AND is_deleted = FALSE")

QA_DEPARTMENT = "质量保证部"


async def _ensure_contact(db: AsyncSession, cache: dict[str, DepartmentContact], department: str) -> DepartmentContact:
    """按部门名取或建联系人行（不提交）。"""
    contact = cache.get(department)
    if contact is not None:
        return contact
    contact = (
        await db.execute(
            select(DepartmentContact).where(
                DepartmentContact.department == department,
                DepartmentContact.is_deleted.is_(False),  # noqa: E712
            )
        )
    ).scalar_one_or_none()
    if contact is None:
        contact = DepartmentContact(department=department, qa_staff_ids=[], gmp_staff_ids=[], additional_contacts=[])
        db.add(contact)
    cache[department] = contact
    return contact


def _append_token(tokens: list[str] | None, token: str) -> list[str]:
    result = list(tokens or [])
    if token and token not in result:
        result.append(token)
    return result


async def seed(dry_run: bool = False) -> dict[str, int]:
    """执行初始化，返回统计（便于脚本输出与回归验证）。"""
    stats: dict[str, Any] = {"departments": 0, "leaders": 0, "qa": 0, "unmatched_leaders": 0}
    async with async_session_factory() as db:
        cache: dict[str, DepartmentContact] = {}

        leaders = (await db.execute(_LEADERS_SQL)).mappings().all()
        for row in leaders:
            department = (row["department"] or "").strip()
            token = (row["open_id"] or "").strip()
            if not department or not token:
                continue
            contact = await _ensure_contact(db, cache, department)
            user_id = (await db.execute(_USER_BY_FEISHU_SQL, {"open_id": token})).scalar_one_or_none()
            if user_id is not None and contact.dept_head_id is None:
                contact.dept_head_id = user_id
            else:
                contact.additional_contacts = _append_token(contact.additional_contacts, token)
                if user_id is None:
                    stats["unmatched_leaders"] += 1
            stats["leaders"] += 1

        qa_rows = (await db.execute(_QA_SQL)).mappings().all()
        for row in qa_rows:
            department = (row["department"] or "").strip() or QA_DEPARTMENT
            token = (row["open_id"] or "").strip()
            if not token:
                continue
            contact = await _ensure_contact(db, cache, department)
            contact.qa_staff_ids = _append_token(contact.qa_staff_ids, token)
            stats["qa"] += 1

        # 审核流的 QA 审核 / QA 负责人审核固定取「质量保证部」，确保该行存在
        await _ensure_contact(db, cache, QA_DEPARTMENT)
        stats["departments"] = len(cache)

        if dry_run:
            await db.rollback()
        else:
            await db.commit()
    return stats


async def main() -> None:
    dry_run = "--dry-run" in sys.argv
    stats = await seed(dry_run=dry_run)
    mode = "（dry-run，未提交）" if dry_run else ""
    print(
        f"部门联系人初始化完成{mode}：部门 {stats['departments']} 个，"
        f"负责人 {stats['leaders']} 条（未匹配用户 {stats['unmatched_leaders']} 条），QA {stats['qa']} 条"
    )


if __name__ == "__main__":
    asyncio.run(main())
