"""HR runtime settings for the Feishu org mirror.

The sync root is a runtime setting stored in ``core.module_settings`` (module
``hr``) and configured from the HR system-settings page. There is deliberately
no built-in default: an unconfigured deployment fails closed (503) instead of
silently scoping to a hardcoded company.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_model import ModuleSetting
from app.core.exceptions import AppException
from app.modules.hr.org_domain import OrgScope

HR_MODULE = "hr"
ORG_SYNC_ROOT_ID_SETTING = "HR_ORG_SYNC_ROOT_DEPARTMENT_ID"
ORG_SYNC_ROOT_NAME_SETTING = "HR_ORG_SYNC_ROOT_DEPARTMENT_NAME"

ORG_SCOPE_SETTING_KEYS: frozenset[str] = frozenset({ORG_SYNC_ROOT_ID_SETTING, ORG_SYNC_ROOT_NAME_SETTING})


async def load_org_scope(session: AsyncSession, *, required: bool = True) -> OrgScope:
    """Read the configured sync root from core.module_settings.

    ``required=True`` (sync / directory paths) raises 503 when either half of
    the pair is unset — an empty scope would mirror the wrong subtree.
    ``required=False`` (settings page) returns empty strings so an operator can
    still read and fix the configuration.
    """
    result = await session.execute(
        select(ModuleSetting).where(
            ModuleSetting.module == HR_MODULE,
            ModuleSetting.key.in_([ORG_SYNC_ROOT_ID_SETTING, ORG_SYNC_ROOT_NAME_SETTING]),
            ModuleSetting.is_deleted.is_(False),
        )
    )
    stored = {row.key: row.value for row in result.scalars().all()}

    department_id = str(stored.get(ORG_SYNC_ROOT_ID_SETTING) or "").strip()
    department_name = str(stored.get(ORG_SYNC_ROOT_NAME_SETTING) or "").strip()

    if required and (not department_id or not department_name):
        raise AppException(status_code=503, message="未配置 HR 组织同步范围")

    return OrgScope(department_id=department_id, department_name=department_name)


async def save_org_scope_value(session: AsyncSession, key: str, value: str) -> None:
    """Upsert one org-scope value into core.module_settings."""
    result = await session.execute(
        select(ModuleSetting).where(ModuleSetting.module == HR_MODULE, ModuleSetting.key == key)
    )
    row = result.scalar_one_or_none()
    if row is None:
        session.add(ModuleSetting(module=HR_MODULE, key=key, value=value, value_type="string"))
    else:
        row.value = value
    await session.flush()
