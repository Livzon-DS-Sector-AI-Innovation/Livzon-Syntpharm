"""把已持有「更新研发报告」的角色补上「评审研发报告」。

报告生成的意见三个接口（提意见 / 处置 / 沉淀示例）由 ``research:report:update``
收紧为 ``research:report:review``。权限码只声明不自动授权，若不回填，升级后原本
能评审的角色会突然 403——用户看到的是按钮失灵，而不是一条可配置的权限差异。

down 不做反向收敛：退回 update 会抹掉「只评审、不改档」这一区分本身，
而权限码仍在，留着授权没有副作用。
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "0120_backfill_report_review_grant"
down_revision = "0119_add_example_source_feedback_promoted"
branch_labels = None
depends_on = None

SOURCE_CODE = "research:report:update"
TARGET_CODE = "research:report:review"


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO permission.role_permissions
                (id, role_id, permission_code, created_at, updated_at, is_deleted)
            SELECT gen_random_uuid(), rp.role_id, :target, now(), now(), false
            FROM permission.role_permissions AS rp
            WHERE rp.permission_code = :source
              AND rp.is_deleted = false
              AND NOT EXISTS (
                  SELECT 1
                  FROM permission.role_permissions AS granted
                  WHERE granted.role_id = rp.role_id
                    AND granted.permission_code = :target
                    AND granted.is_deleted = false
              )
            """
        ).bindparams(source=SOURCE_CODE, target=TARGET_CODE)
    )


def downgrade() -> None:
    # 只清理本条回填产生的授权，不碰管理员后来手工勾选的结果。
    pass
