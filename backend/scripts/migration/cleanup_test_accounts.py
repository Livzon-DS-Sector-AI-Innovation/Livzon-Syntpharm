"""清理测试 / 联调账号（E2E、QA 自动化、手工 test 账号）。

背景（#219）：用户管理页与选人下拉改为只列「系统里真实存在、能登录的账号」后，
历史上的 E2E / QA 测试账号仍会出现在下拉里，存在被误选为业务责任人的风险。

匹配规则（任一命中，逐条打印命中原因供人工核对）：

* ``username`` 前缀：``e2e`` / ``qa_user_`` / ``test``
* 邮箱域名：``@example.com`` / ``@dazah.local`` / ``@test.local``

安全约束：

* 默认 dry-run，只打印清单；加 ``--apply`` 才真正软删除；
* 超管账号一律跳过（即使 username 命中规则）；
* 只置 ``is_deleted=true``，不物理删除，便于回溯；
* 同时把该账号的 ``permission.user_role_grants`` 软删，避免残留授权指向已删账号；
* 不在 e2e 环境执行：``get_or_create_e2e_user`` 会在测试启动时重建。

用法（容器内）::

    /app/.venv/bin/python -m scripts.migration.cleanup_test_accounts
    /app/.venv/bin/python -m scripts.migration.cleanup_test_accounts --apply
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from dataclasses import dataclass
from typing import Any, cast

from sqlalchemy import select, text
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import async_session_factory
from app.platform.identity.models import User
from app.platform.permission.public_api import list_superuser_user_ids

logger = logging.getLogger(__name__)

_USERNAME_PREFIXES = ("e2e", "qa_user_", "test")
_EMAIL_DOMAINS = ("@example.com", "@dazah.local", "@test.local")


@dataclass
class Candidate:
    """一个命中清理规则的账号，附带命中原因与授权条数。"""

    user: User
    reason: str
    grants: int


@dataclass
class CleanupStats:
    scanned: int = 0
    matched: int = 0
    skipped_superuser: int = 0
    deleted: int = 0
    grants_deleted: int = 0


def match_reason(user: User) -> str | None:
    """Return the matched rule description, or None when the account is not a test account."""
    username = (user.username or "").lower()
    for prefix in _USERNAME_PREFIXES:
        if username.startswith(prefix):
            return f"username 前缀 {prefix}"
    email = (user.email or "").lower()
    for domain in _EMAIL_DOMAINS:
        if email.endswith(domain):
            return f"邮箱域名 {domain}"
    return None


async def _count_grants(session: AsyncSession, user_ids: list[str]) -> dict[str, int]:
    """Count active role grants per user (parameterized, no string interpolation)."""
    if not user_ids:
        return {}
    result = await session.execute(
        text(
            "SELECT user_id::text, count(*) FROM permission.user_role_grants "
            "WHERE is_deleted = false AND user_id = ANY(CAST(:ids AS uuid[])) "
            "GROUP BY user_id"
        ),
        {"ids": user_ids},
    )
    return {row[0]: int(row[1]) for row in result.all()}


async def collect_candidates(session: AsyncSession) -> tuple[list[Candidate], int, int]:
    """Return ``(matched candidates, skipped superusers, total scanned accounts)``."""
    result = await session.execute(
        select(User).where(User.is_deleted.is_(False)).order_by(User.created_at.asc())
    )
    users = list(result.scalars().all())
    super_ids = {str(uid) for uid in await list_superuser_user_ids(session)}

    reasons: dict[str, str] = {}
    matched_users: list[User] = []
    skipped_superuser = 0
    for user in users:
        reason = match_reason(user)
        if reason is None:
            continue
        if str(user.id) in super_ids:
            skipped_superuser += 1
            logger.warning("跳过超管账号: username=%s id=%s", user.username, user.id)
            continue
        reasons[str(user.id)] = reason
        matched_users.append(user)

    grants = await _count_grants(session, list(reasons))
    candidates = [
        Candidate(user=user, reason=reasons[str(user.id)], grants=grants.get(str(user.id), 0))
        for user in matched_users
    ]
    return candidates, skipped_superuser, len(users)


async def run(*, apply: bool) -> CleanupStats:
    stats = CleanupStats()
    async with async_session_factory() as session:
        candidates, skipped_superuser, scanned = await collect_candidates(session)
        stats.scanned = scanned
        stats.matched = len(candidates)
        stats.skipped_superuser = skipped_superuser

        if not candidates:
            print("未发现匹配的测试账号。")
            return stats

        print(f"{'ID':38}  {'username':22} {'status':8} {'grants':6}  原因")
        for item in candidates:
            user = item.user
            print(
                f"{str(user.id):38}  {(user.username or '-'):22} {user.status:8} "
                f"{item.grants:<6}  {item.reason}  ({user.name})"
            )

        if not apply:
            print(f"\n[dry-run] 命中 {len(candidates)} 个账号；确认无误后加 --apply 执行软删除。")
            return stats

        user_ids = [str(item.user.id) for item in candidates]
        grant_result = cast(
            CursorResult[Any],
            await session.execute(
                text(
                    "UPDATE permission.user_role_grants SET is_deleted = true, updated_at = now() "
                    "WHERE is_deleted = false AND user_id = ANY(CAST(:ids AS uuid[]))"
                ),
                {"ids": user_ids},
            ),
        )
        user_result = cast(
            CursorResult[Any],
            await session.execute(
                text(
                    "UPDATE identity.users SET is_deleted = true, updated_at = now() "
                    "WHERE is_deleted = false AND id = ANY(CAST(:ids AS uuid[]))"
                ),
                {"ids": user_ids},
            ),
        )
        await session.commit()
        stats.deleted = int(user_result.rowcount or 0)
        stats.grants_deleted = int(grant_result.rowcount or 0)
        print(f"\n[apply] 已软删除账号 {stats.deleted} 个、授权记录 {stats.grants_deleted} 条。")
    return stats


def main() -> int:
    parser = argparse.ArgumentParser(description="清理 E2E / QA / test 测试账号（默认 dry-run）")
    parser.add_argument("--apply", action="store_true", help="执行软删除（默认只打印清单）")
    parser.add_argument("--force", action="store_true", help="允许在 APP_ENV=e2e 环境执行（默认拒绝）")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    if get_settings().APP_ENV == "e2e" and not args.force:
        print("拒绝执行：APP_ENV=e2e 环境下账号会在测试启动时被重建；确需执行请显式加 --force。")
        return 2
    stats = asyncio.run(run(apply=args.apply))
    logger.info(
        "cleanup done: scanned=%s matched=%s deleted=%s grants=%s skipped_superuser=%s",
        stats.scanned,
        stats.matched,
        stats.deleted,
        stats.grants_deleted,
        stats.skipped_superuser,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
