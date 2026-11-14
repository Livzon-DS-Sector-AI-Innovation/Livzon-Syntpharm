"""HR runtime settings for the Feishu org mirror.

The sync scope is a runtime setting stored in ``core.module_settings`` (module
``hr``) and configured from the HR system-settings page. ``HR_ORG_SYNC_ROOTS``
holds an ordered JSON list of company roots; the older id/name pair is kept as
a read fallback for existing deployments. There is deliberately no built-in
default: an unconfigured deployment fails closed (503).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_model import ModuleSetting
from app.core.exceptions import AppException
from app.modules.hr.org_domain import OrgScope, OrgScopes

logger = logging.getLogger(__name__)

HR_MODULE = "hr"
ORG_SYNC_ROOTS_SETTING = "HR_ORG_SYNC_ROOTS"
ORG_SYNC_ROOT_ID_SETTING = "HR_ORG_SYNC_ROOT_DEPARTMENT_ID"
ORG_SYNC_ROOT_NAME_SETTING = "HR_ORG_SYNC_ROOT_DEPARTMENT_NAME"

ORG_SCOPE_SETTING_KEYS: frozenset[str] = frozenset(
    {ORG_SYNC_ROOTS_SETTING, ORG_SYNC_ROOT_ID_SETTING, ORG_SYNC_ROOT_NAME_SETTING}
)


def _parse_roots(raw: str) -> list[OrgScope]:
    """Parse and validate the JSON root list; raise 503 on corrupt configuration."""
    try:
        payload: Any = json.loads(raw)
    except (TypeError, ValueError) as exc:
        raise AppException(status_code=503, message="HR 组织同步范围配置格式错误") from exc
    if not isinstance(payload, list):
        raise AppException(status_code=503, message="HR 组织同步范围配置必须是数组")

    roots: list[OrgScope] = []
    seen: set[str] = set()
    for item in payload:
        if not isinstance(item, dict):
            raise AppException(status_code=503, message="HR 组织同步范围条目格式错误")
        department_id = str(item.get("department_id") or "").strip()
        name = str(item.get("name") or "").strip()
        if not department_id or not name:
            raise AppException(status_code=503, message="HR 组织同步范围缺少部门 ID 或名称")
        if department_id in seen:
            raise AppException(status_code=503, message="HR 组织同步范围包含重复的部门 ID")
        seen.add(department_id)
        roots.append(OrgScope(department_id=department_id, department_name=name))
    return roots


async def load_org_scopes(session: AsyncSession, *, required: bool = True) -> OrgScopes:
    """Read all configured company roots from ``core.module_settings``.

    ``HR_ORG_SYNC_ROOTS`` wins; when absent (older deployments) the single
    id/name pair is used. ``required=True`` raises 503 when no scope is
    configured; ``required=False`` (settings page) returns an empty set so the
    operator can still read and fix the configuration.
    """
    result = await session.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == HR_MODULE,
            ModuleSetting.key.in_(
                [ORG_SYNC_ROOTS_SETTING, ORG_SYNC_ROOT_ID_SETTING, ORG_SYNC_ROOT_NAME_SETTING]
            ),
            ModuleSetting.is_deleted.is_(False),
        )
    )
    stored = {row.key: row.value for row in result.scalars().all()}

    roots_raw = str(stored.get(ORG_SYNC_ROOTS_SETTING) or "").strip()
    department_id = str(stored.get(ORG_SYNC_ROOT_ID_SETTING) or "").strip()
    department_name = str(stored.get(ORG_SYNC_ROOT_NAME_SETTING) or "").strip()
    legacy_roots = (
        [OrgScope(department_id=department_id, department_name=department_name)]
        if department_id and department_name
        else []
    )

    if roots_raw:
        try:
            roots = _parse_roots(roots_raw)
        except AppException:
            if required:
                raise
            # Settings page must stay usable so the bad value can be overwritten.
            logger.warning(
                "HR_ORG_SYNC_ROOTS 配置无效，设置页回退到旧版单根部门配置",
                extra={"biz_module": "hr"},
            )
            roots = legacy_roots
    else:
        roots = legacy_roots

    if required and not roots:
        raise AppException(status_code=503, message="未配置 HR 组织同步范围")
    return OrgScopes(tuple(roots))


async def load_org_scope(session: AsyncSession, *, required: bool = True) -> OrgScope:
    """Backward-compatible single-root view (first configured root)."""
    scopes = await load_org_scopes(session, required=required)
    if scopes.roots:
        return scopes.roots[0]
    return OrgScope(department_id="", department_name="")


async def save_org_scopes(session: AsyncSession, roots: list[OrgScope]) -> None:
    """Upsert the JSON root list into ``core.module_settings``."""
    payload = json.dumps(
        [{"department_id": root.department_id, "name": root.department_name} for root in roots],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    result = await session.execute(
        select(ModuleSetting).where(ModuleSetting.module == HR_MODULE, ModuleSetting.key == ORG_SYNC_ROOTS_SETTING)
    )
    row = result.scalar_one_or_none()
    if row is None:
        session.add(
            ModuleSetting(
                module=HR_MODULE,
                key=ORG_SYNC_ROOTS_SETTING,
                value=payload,
                value_type="json",
            )
        )
    else:
        row.value = payload
        row.value_type = "json"
        row.is_deleted = False
    await session.flush()


async def save_org_scope_value(session: AsyncSession, key: str, value: str) -> None:
    """Upsert one legacy org-scope value into ``core.module_settings``."""
    result = await session.execute(
        select(ModuleSetting).where(ModuleSetting.module == HR_MODULE, ModuleSetting.key == key)
    )
    row = result.scalar_one_or_none()
    if row is None:
        session.add(ModuleSetting(module=HR_MODULE, key=key, value=value, value_type="string"))
    else:
        row.value = value
        row.value_type = "string"
        row.is_deleted = False
    await session.flush()
