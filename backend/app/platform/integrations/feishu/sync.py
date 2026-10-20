"""Generic Feishu-to-local-DB sync orchestration.

Provides a single `run_sync` helper that replaces the copy-pasted
"fetch -> parse -> upsert -> stats" pattern found in every HR and
product service method.
"""

import json
import logging
import time
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select

from app.core.database import async_session_factory

logger = logging.getLogger(__name__)

SyncStats = dict[str, int]


async def run_sync(
    *,
    fetch_records: Callable[[], Coroutine[Any, Any, list[dict[str, Any]]]],
    parse_record: Callable[[dict[str, Any]], dict[str, Any] | None],
    upsert_record: Callable[[dict[str, Any]], Coroutine[Any, Any, None]],
    get_existing: Callable[[str], Coroutine[Any, Any, Any | None]],
    get_record_id: Callable[[dict[str, Any]], str | None],
    post_process: Callable[[Any, dict[str, Any]], Coroutine[Any, Any, None]] | None = None,
) -> SyncStats:
    """Generic sync orchestrator: fetch -> parse -> upsert -> stats.

    Args:
        fetch_records: Coroutine that returns raw Feishu record dicts.
        parse_record: Callable that converts a raw record to local DB kwargs
                      (returns None to skip).
        upsert_record: Coroutine that writes/updates the local DB record.
        get_existing: Coroutine that fetches the local DB record by its key
                      (used to distinguish created vs updated).
        get_record_id: Callable that extracts the unique key from parsed data.
        post_process: Optional coroutine called after a successful upsert,
                      receiving (existing_record, parsed_data).

    Returns:
        {"created": int, "updated": int, "failed": int, "total": int}
    """
    raw_records = await fetch_records()
    stats: SyncStats = {
        "created": 0,
        "updated": 0,
        "failed": 0,
        "total": len(raw_records),
    }

    for rec in raw_records:
        try:
            parsed = parse_record(rec)
            if not parsed:
                stats["failed"] += 1
                continue

            rid = get_record_id(parsed)
            if not rid:
                stats["failed"] += 1
                continue

            await upsert_record(parsed)

            existing = await get_existing(rid)
            if existing and existing.created_at and _is_newly_created(existing):
                stats["created"] += 1
            else:
                stats["updated"] += 1

            if post_process:
                await post_process(existing, parsed)

        except Exception:
            logger.exception("Failed to sync Feishu record %s", rec.get("record_id"))
            stats["failed"] += 1

    return stats


def _is_newly_created(existing: Any) -> bool:
    """Heuristic: record created within last 60 seconds -> treat as 'created'."""

    created_at = existing.created_at
    if not created_at:
        return False
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=UTC)
    return (datetime.now(UTC) - created_at).total_seconds() < 60  # type: ignore[no-any-return]


def _parse_user_record(rec: dict[str, Any]) -> dict[str, Any] | None:
    open_id = rec.get("open_id")
    if not open_id:
        return None
    # 部门归属优先用「遍历部门」反推的结果（dept_ids）；
    # contact 用户接口自带的 department_ids 需额外权限，未开通时为空
    dept_ids = rec.get("dept_ids") or rec.get("department_ids") or []
    dept_ids_json = json.dumps(dept_ids) if dept_ids else None
    return {
        "open_id": open_id,
        "user_id": rec.get("user_id") or None,
        "union_id": rec.get("union_id") or None,
        "name": rec.get("name", ""),
        "en_name": rec.get("en_name", ""),
        "employee_no": rec.get("employee_no") or None,
        "email": rec.get("email") or None,
        "mobile": rec.get("mobile") or None,
        "department": rec.get("dept_name", ""),
        "position": rec.get("job_title") or None,
        "avatar_url": rec.get("avatar_url") or rec.get("avatar_key") or None,
        "avatar_thumb": rec.get("avatar_thumb") or None,
        "avatar_middle": rec.get("avatar_middle") or None,
        "avatar_big": rec.get("avatar_big") or None,
        "feishu_department_ids": dept_ids_json,
        "is_resigned": bool(rec.get("is_resigned", False)),
        "is_frozen": bool(rec.get("is_frozen", False)),
    }


async def _upsert_user(parsed: dict[str, Any]) -> None:
    from app.platform.identity.models import User

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.feishu_open_id == parsed["open_id"]))
        existing = result.scalar_one_or_none()
        if existing:
            existing.name = parsed["name"] or existing.name
            existing.en_name = parsed["en_name"] or existing.en_name
            existing.employee_no = parsed["employee_no"] or existing.employee_no
            existing.email = parsed["email"] or existing.email
            existing.mobile = parsed["mobile"] or existing.mobile
            existing.position = parsed["position"] or existing.position
            existing.avatar_url = parsed["avatar_url"] or existing.avatar_url
            existing.avatar_thumb = parsed["avatar_thumb"] or existing.avatar_thumb
            existing.avatar_middle = parsed["avatar_middle"] or existing.avatar_middle
            existing.avatar_big = parsed["avatar_big"] or existing.avatar_big
            existing.feishu_union_id = parsed["union_id"] or existing.feishu_union_id
            if not existing.department:
                existing.department = parsed["department"]
            existing.feishu_department_ids = parsed["feishu_department_ids"]
            # user_id 需 contact:user.employee_id:readonly（集团审核中），为空时不覆盖
            if not existing.feishu_user_id and parsed["user_id"]:
                existing.feishu_user_id = parsed["user_id"]
            # 离职/冻结：开关开启时自动禁用账号（不自动恢复，恢复需人工；跳过超管）
            if parsed.get("is_resigned") or parsed.get("is_frozen"):
                await _maybe_disable_resigned(db, existing)
        else:
            db.add(
                User(
                    name=parsed["name"],
                    en_name=parsed["en_name"],
                    feishu_user_id=parsed["user_id"],
                    feishu_open_id=parsed["open_id"],
                    employee_no=parsed["employee_no"],
                    email=parsed["email"],
                    mobile=parsed["mobile"],
                    department=parsed["department"],
                    position=parsed["position"],
                    avatar_url=parsed["avatar_url"],
                    avatar_thumb=parsed["avatar_thumb"],
                    avatar_middle=parsed["avatar_middle"],
                    avatar_big=parsed["avatar_big"],
                    feishu_union_id=parsed["union_id"],
                    feishu_department_ids=parsed["feishu_department_ids"],
                )
            )
        await db.commit()


async def _maybe_disable_resigned(db: Any, user: Any) -> None:
    """离职/冻结的成员：开关开启时自动禁用本地账号。

    - 开关：`identity.AUTO_DISABLE_RESIGNED`（默认 false，关闭）；
    - 跳过超级管理员（避免把最后一个超管锁死）；
    - 只禁用、不自动恢复（成员复职后需管理员手动启用）。
    """
    from app.platform.permission.public_api import user_is_superuser
    from app.shared.config_reader import get_module_setting_bool

    if not await get_module_setting_bool("identity", "AUTO_DISABLE_RESIGNED", False):
        return
    if await user_is_superuser(db, user):
        return
    user.status = "disabled"


async def _get_existing_user(open_id: str) -> Any:
    from app.platform.identity.models import User

    async with async_session_factory() as db:
        result = await db.execute(select(User).where(User.feishu_open_id == open_id))
        return result.scalar_one_or_none()


# ── Department sync ─────────────────────────────────────────────────


async def sync_departments(
    root_dept_id: str | None,
    *,
    app_id: str | None = None,
    app_secret: str | None = None,
) -> dict[str, Any]:
    """Sync department structure from Feishu starting at root_dept_id.

    Uses BFS to fetch all departments under root, then upserts into
    identity.departments table.

    Returns stats dict with dept_count, elapsed.
    """
    from app.platform.identity.models import Department
    from app.platform.integrations.feishu.contact import get_all_departments

    t0 = time.time()
    logger.info("sync_departments starting (root=%s)", root_dept_id)

    async def fetch_depts() -> list[dict[str, Any]]:
        # root_dept_id 为空时由 get_all_departments 自行决定起点
        # （优先应用可见范围内的部门，避免从根部门 "0" 拉时报 40004）
        return await get_all_departments(root_department_id=root_dept_id or None)

    def parse_dept(rec: dict[str, Any]) -> dict[str, Any] | None:
        dept_id = rec.get("department_id")
        if not dept_id:
            return None
        return {
            "department_id": dept_id,
            "name": rec.get("name", ""),
            "parent_department_id": rec.get("parent_department_id", ""),
            "leader_user_id": rec.get("leader_user_id", ""),
            "member_count": rec.get("member_count", 0),
            "status_is_deleted": rec.get("status_is_deleted", False),
            "order": rec.get("order", 0),
        }

    async def upsert_dept(parsed: dict[str, Any]) -> None:
        async with async_session_factory() as db:
            result = await db.execute(
                select(Department).where(Department.feishu_department_id == parsed["department_id"])
            )
            existing = result.scalar_one_or_none()
            if existing:
                existing.name = parsed["name"]
                existing.parent_feishu_department_id = parsed["parent_department_id"]
                existing.leader_user_id = parsed["leader_user_id"]
                existing.member_count = parsed["member_count"]
                existing.status_is_deleted = parsed["status_is_deleted"]
                existing.order = parsed["order"]
            else:
                db.add(
                    Department(
                        feishu_department_id=parsed["department_id"],
                        name=parsed["name"],
                        parent_feishu_department_id=parsed["parent_department_id"],
                        leader_user_id=parsed["leader_user_id"],
                        member_count=parsed["member_count"],
                        status_is_deleted=parsed["status_is_deleted"],
                        order=parsed["order"],
                    )
                )
            await db.commit()

    async def get_existing(dept_id: str) -> Any:
        async with async_session_factory() as db:
            result = await db.execute(select(Department).where(Department.feishu_department_id == dept_id))
            return result.scalar_one_or_none()

    stats = await run_sync(
        fetch_records=fetch_depts,
        parse_record=parse_dept,
        upsert_record=upsert_dept,
        get_existing=get_existing,
        get_record_id=lambda r: r["department_id"],
    )

    elapsed = time.time() - t0
    logger.info(
        "sync_departments done: %d depts (%d created, %d updated) in %.1fs",
        stats["total"],
        stats["created"],
        stats["updated"],
        elapsed,
    )
    return {"dept_count": stats["total"], "elapsed": round(elapsed, 1)}


# ── Member sync ─────────────────────────────────────────────────────


async def sync_members(
    target_dept_id: str | None = None,
    *,
    app_id: str | None = None,
    app_secret: str | None = None,
) -> dict[str, Any]:
    """同步可见范围内的成员到 identity.users。

    不传 target_dept_id 时从「应用可见范围内的部门」出发
    （可见范围通常不含根部门 "0"，从 "0" 拉会报 40004）。
    归属部门由「遍历部门」反推（contact 用户接口的 department_ids 需额外权限）。
    仅需 contact:user.base:readonly：姓名 / 英文名 / 头像 / open_id / union_id；
    工号、职务、邮箱、手机号需集团审核的权限，未开通时为空。

    Returns stats dict with user_count, dept_count, elapsed.
    """
    from app.platform.integrations.feishu.contact import (
        find_users_by_department,
        get_all_departments,
    )

    t0 = time.time()
    logger.info("sync_members starting (target=%s)", target_dept_id or "(自动：可见范围内的部门)")

    try:
        all_depts = await get_all_departments(root_department_id=target_dept_id or None)
    except Exception:
        logger.exception("Failed to fetch departments under %s", target_dept_id)
        all_depts = []

    dept_ids = [d["department_id"] for d in all_depts]
    if not dept_ids and target_dept_id:
        dept_ids = [target_dept_id]
    dept_ids = list(dict.fromkeys(dept_ids))

    async def fetch_users() -> list[dict[str, Any]]:
        """按部门拉取成员，并按 open_id 合并（同一人常属于多个部门）。"""
        merged: dict[str, dict[str, Any]] = {}
        fetch_users.errors = []  # type: ignore[attr-defined]
        for dept_id in dept_ids:
            try:
                users = await find_users_by_department(dept_id)
                dept_name = next(
                    (d["name"] for d in all_depts if d["department_id"] == dept_id),
                    "",
                )
                for u in users:
                    open_id = u.get("open_id")
                    if not open_id:
                        continue
                    item = merged.get(open_id)
                    if item is None:
                        item = dict(u)
                        item["dept_ids"] = []
                        item["dept_names"] = []
                        merged[open_id] = item
                    if dept_id not in item["dept_ids"]:
                        item["dept_ids"].append(dept_id)
                    if dept_name and dept_name not in item["dept_names"]:
                        item["dept_names"].append(dept_name)
                    # 单部门字段（兼容旧解析）：取第一个部门
                    item["dept_name"] = item["dept_names"][0] if item["dept_names"] else ""
                    item["dept_id"] = item["dept_ids"][0] if item["dept_ids"] else ""
            except Exception as exc:
                logger.exception("Failed to fetch users from dept %s", dept_id)
                fetch_users.errors.append(f"{dept_id}: {exc}")  # type: ignore[attr-defined]
        return list(merged.values())

    fetch_users.errors = []  # type: ignore[attr-defined]

    stats = await run_sync(
        fetch_records=fetch_users,
        parse_record=_parse_user_record,
        upsert_record=_upsert_user,
        get_existing=_get_existing_user,
        get_record_id=lambda r: r["open_id"],
    )

    elapsed = time.time() - t0
    logger.info(
        "sync_members done: %d users from %d depts (%d created, %d updated) in %.1fs",
        stats["total"],
        len(dept_ids),
        stats["created"],
        stats["updated"],
        elapsed,
    )
    return {
        "user_count": stats["total"],
        "dept_count": len(dept_ids),
        "errors": fetch_users.errors,  # type: ignore[attr-defined]
        "elapsed": round(elapsed, 1),
    }


async def sync_users_by_ids(
    user_ids: list[str],
    *,
    user_id_type: str = "user_id",
    app_id: str | None = None,
    app_secret: str | None = None,
) -> dict[str, Any]:
    """Sync explicitly authorized Feishu users by user ID/open ID."""
    from app.platform.integrations.feishu.contact import get_user_detail

    t0 = time.time()
    unique_user_ids = [uid for uid in dict.fromkeys(user_ids) if uid]
    logger.info("sync_users_by_ids starting (%d users)", len(unique_user_ids))

    async def fetch_users() -> list[dict[str, Any]]:
        users: list[dict[str, Any]] = []
        for user_id in unique_user_ids:
            try:
                user = await get_user_detail(  # type: ignore[call-arg]
                    user_id,
                    user_id_type=user_id_type,
                    app_id=app_id,
                    app_secret=app_secret,
                )
                if user:
                    users.append(user)
            except Exception:
                logger.exception("Failed to fetch Feishu user %s", user_id)
        return users

    stats = await run_sync(
        fetch_records=fetch_users,
        parse_record=_parse_user_record,
        upsert_record=_upsert_user,
        get_existing=_get_existing_user,
        get_record_id=lambda r: r["open_id"],
    )

    elapsed = time.time() - t0
    logger.info(
        "sync_users_by_ids done: %d users (%d created, %d updated) in %.1fs",
        stats["total"],
        stats["created"],
        stats["updated"],
        elapsed,
    )
    return {"user_count": stats["total"], "elapsed": round(elapsed, 1)}
