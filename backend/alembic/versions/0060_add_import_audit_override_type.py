"""add override_type to equipment.import_audit_logs

Revision ID: 0060_add_import_audit_override_type
Revises: 0059
Create Date: 2026-09-11

背景:
    原 `ab38b62cf60e_add_override_type_to_import_audit_logs.py` 存在两处致命缺陷:
    1. down_revision 指向磁盘上不存在的 '6d70b69e00e4' -> 迁移链断裂,
       导致 `alembic upgrade head` 报 "Can't locate revision";
    2. upgrade() 为 pass（空迁移）, 未实际建列。
    本迁移按 AGENTS.md 命名规范（4 位数字 + 描述性名称）重建同一变更。

兼容性说明:
    部分环境（含本机 dev 库 dazah）的 `override_type` 列已由 ORM create_all
    先行创建。因此这里用 information_schema 做存在性判断后再 ALTER,
    保证「已有列的环境」与「全新环境」都能幂等通过。
"""
from alembic import op

revision = "0060_add_import_audit_override_type"
down_revision = "0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'equipment'
                  AND table_name   = 'import_audit_logs'
                  AND column_name  = 'override_type'
            ) THEN
                ALTER TABLE equipment.import_audit_logs
                    ADD COLUMN override_type VARCHAR(20) NULL;

                COMMENT ON COLUMN equipment.import_audit_logs.override_type
                    IS '覆盖类型: normal/force';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE equipment.import_audit_logs
            DROP COLUMN IF EXISTS override_type;
        """
    )
