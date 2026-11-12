"""HR runtime settings for the Feishu org mirror.

The sync root is a runtime setting stored in ``hr.system_settings`` so it can
be changed from the HR system-settings page without a deployment. The current
company is the default when the rows are absent.
"""

from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.hr.org_domain import (
    DEFAULT_SYNC_ROOT_DEPARTMENT_ID,
    DEFAULT_SYNC_ROOT_DEPARTMENT_NAME,
    OrgScope,
)

ORG_SYNC_ROOT_ID_SETTING = "HR_ORG_SYNC_ROOT_DEPARTMENT_ID"
ORG_SYNC_ROOT_NAME_SETTING = "HR_ORG_SYNC_ROOT_DEPARTMENT_NAME"

ORG_SCOPE_SETTING_DEFAULTS: dict[str, str] = {
    ORG_SYNC_ROOT_ID_SETTING: DEFAULT_SYNC_ROOT_DEPARTMENT_ID,
    ORG_SYNC_ROOT_NAME_SETTING: DEFAULT_SYNC_ROOT_DEPARTMENT_NAME,
}


async def load_org_scope(session: AsyncSession) -> OrgScope:
    """Read the configured sync root, falling back to the current company."""
    result = await session.execute(
        text("SELECT key, value FROM hr.system_settings WHERE key IN (:root_id_key, :root_name_key)"),
        {"root_id_key": ORG_SYNC_ROOT_ID_SETTING, "root_name_key": ORG_SYNC_ROOT_NAME_SETTING},
    )
    stored = {row[0]: row[1] for row in result.fetchall()}

    department_id = str(stored.get(ORG_SYNC_ROOT_ID_SETTING) or "").strip()
    department_name = str(stored.get(ORG_SYNC_ROOT_NAME_SETTING) or "").strip()
    return OrgScope(
        department_id=department_id or DEFAULT_SYNC_ROOT_DEPARTMENT_ID,
        department_name=department_name or DEFAULT_SYNC_ROOT_DEPARTMENT_NAME,
    )
