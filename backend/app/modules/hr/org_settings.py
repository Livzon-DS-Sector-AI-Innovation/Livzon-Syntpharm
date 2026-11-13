"""HR runtime settings for the Feishu org mirror.

The sync root is a runtime setting stored in ``core.module_settings`` (module
``hr``) so it can be changed from the HR system-settings page without a
deployment. The current company is the default when the rows are absent.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config_model import ModuleSetting
from app.modules.hr.org_domain import (
    DEFAULT_SYNC_ROOT_DEPARTMENT_ID,
    DEFAULT_SYNC_ROOT_DEPARTMENT_NAME,
    OrgScope,
)

HR_MODULE = "hr"
ORG_SYNC_ROOT_ID_SETTING = "HR_ORG_SYNC_ROOT_DEPARTMENT_ID"
ORG_SYNC_ROOT_NAME_SETTING = "HR_ORG_SYNC_ROOT_DEPARTMENT_NAME"

ORG_SCOPE_SETTING_DEFAULTS: dict[str, str] = {
    ORG_SYNC_ROOT_ID_SETTING: DEFAULT_SYNC_ROOT_DEPARTMENT_ID,
    ORG_SYNC_ROOT_NAME_SETTING: DEFAULT_SYNC_ROOT_DEPARTMENT_NAME,
}


async def load_org_scope(session: AsyncSession) -> OrgScope:
    """Read the configured sync root from core.module_settings."""
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
    return OrgScope(
        department_id=department_id or DEFAULT_SYNC_ROOT_DEPARTMENT_ID,
        department_name=department_name or DEFAULT_SYNC_ROOT_DEPARTMENT_NAME,
    )


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
