"""move HR org-scope settings to core.module_settings

Revision ID: 0137_hr_org_scope_to_module_settings
Revises: 0136_revert_identity_org_hr_fields
Create Date: 2026-11-13

Runtime configuration belongs in ``core.module_settings``. Move the two
org-sync root keys out of the legacy ``hr.system_settings`` table so the HR
org sync reads the standard runtime-config store.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0137_hr_org_scope_to_module_settings"
down_revision: str = "0136_revert_identity_org_hr_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_KEYS = ("HR_ORG_SYNC_ROOT_DEPARTMENT_ID", "HR_ORG_SYNC_ROOT_DEPARTMENT_NAME")


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO core.module_settings (
                id, module, key, value, value_type, created_at, updated_at, is_deleted
            )
            SELECT gen_random_uuid(), 'hr', key, value, 'string', now(), now(), false
            FROM hr.system_settings
            WHERE key IN :keys
            ON CONFLICT (module, key) DO NOTHING
            """
        ).bindparams(sa.bindparam("keys", expanding=True, value=list(_KEYS)))
    )
    op.execute(
        sa.text("DELETE FROM hr.system_settings WHERE key IN :keys").bindparams(
            sa.bindparam("keys", expanding=True, value=list(_KEYS))
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO hr.system_settings (key, value, updated_at)
            SELECT key, value, now()
            FROM core.module_settings
            WHERE module = 'hr' AND key IN :keys
            ON CONFLICT (key) DO NOTHING
            """
        ).bindparams(sa.bindparam("keys", expanding=True, value=list(_KEYS)))
    )
    op.execute(
        sa.text("DELETE FROM core.module_settings WHERE module = 'hr' AND key IN :keys").bindparams(
            sa.bindparam("keys", expanding=True, value=list(_KEYS))
        )
    )
