"""把 HR 员工档案同步进系统用户（账号）表。

背景（issue #219）：人员主数据搬到 ``hr.employee_profiles`` 后，系统管理的
「用户管理」列表仍以 ``identity.users`` 为基表；HR 里存在、但从未登录也未被
授权过的员工不会出现在该列表里，管理员无法在用户管理页直接给他们建号/授权。

本脚本做一次性/可重复的数据对齐：

* 按 ``open_id`` 匹配已有账号 → 用 HR 的姓名 / 工号刷新登录快照；
* 没有账号的在任员工 → 建最小账号（无密码、``auth_source=feishu``），
  员工首次飞书登录时按 ``open_id`` 认领同一行；
* 不写 ``department`` / ``position`` / ``feishu_department_ids``：这些字段的
  展示已由 HR 装配（``GET /identity/users``），停止写入避免二次冗余；
* 不覆盖已有账号的 ``username`` / 密码 / 状态（已禁用的保持禁用）。

幂等：重复执行只会补齐差异，不会重复建号。

用法（容器内）::

    /app/.venv/bin/python -m scripts.migration.sync_hr_profiles_to_identity_users --dry-run
    /app/.venv/bin/python -m scripts.migration.sync_hr_profiles_to_identity_users --apply
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.modules.hr.models import EmployeeProfile
from app.platform.identity.models import User
from app.platform.identity.service import allocate_default_username

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    profiles: int = 0
    matched: int = 0
    created: int = 0
    renamed: int = 0
    employee_no_filled: int = 0
    skipped_without_name: int = 0


async def _sync(session: AsyncSession, *, apply: bool) -> SyncStats:
    stats = SyncStats()

    result = await session.execute(
        select(EmployeeProfile).where(
            EmployeeProfile.is_deleted.is_(False),
            EmployeeProfile.is_current.is_(True),
            EmployeeProfile.open_id != "",
        )
    )
    profiles = list(result.scalars().all())
    stats.profiles = len(profiles)

    open_ids = [profile.open_id for profile in profiles]
    existing = await session.execute(select(User).where(User.feishu_open_id.in_(open_ids), User.is_deleted.is_(False)))
    users_by_open_id = {user.feishu_open_id: user for user in existing.scalars().all() if user.feishu_open_id}

    for profile in profiles:
        name = (profile.name or "").strip()
        if not name:
            stats.skipped_without_name += 1
            continue

        user = users_by_open_id.get(profile.open_id)
        if user is None:
            stats.created += 1
            if not apply:
                continue
            user = User(
                name=name,
                username=await allocate_default_username(session),
                feishu_open_id=profile.open_id,
                employee_no=(profile.employee_no or None),
                status="active",
                auth_source="feishu",
            )
            session.add(user)
            await session.flush()
            users_by_open_id[profile.open_id] = user
            logger.info("创建账号: open_id=%s name=%s user_id=%s", profile.open_id, name, user.id)
            continue

        stats.matched += 1
        changed = False
        if user.name != name:
            stats.renamed += 1
            if apply:
                user.name = name
            changed = True
        if not user.employee_no and profile.employee_no:
            stats.employee_no_filled += 1
            if apply:
                user.employee_no = profile.employee_no
            changed = True
        if changed and apply:
            logger.info("刷新账号快照: open_id=%s user_id=%s", profile.open_id, user.id)

    if apply:
        await session.commit()
    return stats


async def main() -> None:
    parser = argparse.ArgumentParser(description="HR 员工档案 → 系统用户账号 同步")
    parser.add_argument("--apply", action="store_true", help="实际写入；缺省为 dry-run")
    parser.add_argument("--dry-run", action="store_true", help="只统计差异，不写库")
    args = parser.parse_args()
    apply = args.apply and not args.dry_run

    async with async_session_factory() as session:
        stats = await _sync(session, apply=apply)

    mode = "APPLY" if apply else "DRY-RUN"
    print(f"[{mode}] HR 在任档案 {stats.profiles} 条")
    print(f"  已匹配账号        : {stats.matched}")
    print(f"  需新建账号        : {stats.created}")
    print(f"  姓名需刷新        : {stats.renamed}")
    print(f"  工号需补齐        : {stats.employee_no_filled}")
    print(f"  缺姓名跳过        : {stats.skipped_without_name}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    asyncio.run(main())
