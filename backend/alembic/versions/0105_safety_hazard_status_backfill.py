"""safety hazard ledger status backfill

Revision ID: 0105_safety_hazard_status_backfill
Revises: 0094_safety_hazard_ledger_fields
Create Date: 2026-11-04

0094 把 status 收敛为「关闭状态」（open / closed），但此前 status 没有任何写入方，
存量记录均为默认值 open，与 rectification_status='closed' 的实际业务状态不一致：
台账按 status 显示「未关闭」，详情页按 rectification_status 显示「整改已关闭」。

本迁移按 rectification_status 回填存量数据，不改表结构。只动 safety schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0105_safety_hazard_status_backfill"
down_revision: str = "0094_safety_hazard_ledger_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_BACKFILL_SQL = """
UPDATE safety.hazard_reports
SET status = 'closed',
    closed_at = COALESCE(closed_at, updated_at)
WHERE rectification_status = 'closed'
  AND status <> 'closed'
"""


def upgrade() -> None:
    op.execute(sa.text(_BACKFILL_SQL))


def downgrade() -> None:
    # 纯数据回填，无法区分回填前后的行，不做回滚
    pass
