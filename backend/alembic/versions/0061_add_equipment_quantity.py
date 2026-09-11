"""add quantity to equipment.equipments

Revision ID: 0061_add_equipment_quantity
Revises: 0060_add_import_audit_override_type
Create Date: 2026-09-11

背景:
    设备台账 Excel（`202606sbgz.xls`）含「数量」列，FIELD_MAP 已映射为
    `quantity`，但 Equipment 模型此前无此字段，导致 v4 批量导入走
    create 分支时抛 `TypeError: 'quantity' is an invalid keyword argument
    for Equipment`，该行被丢弃。

    本迁移补上该列，使导入数据不再丢失。

兼容性说明:
    沿用 0060 的幂等写法：先用 information_schema 判断列是否存在再 ALTER，
    保证「已由 ORM create_all 先行建列的环境」与「全新环境」都能通过。
"""
from alembic import op

revision = "0061_add_equipment_quantity"
down_revision = "0060_add_import_audit_override_type"
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
                  AND table_name   = 'equipments'
                  AND column_name  = 'quantity'
            ) THEN
                ALTER TABLE equipment.equipments
                    ADD COLUMN quantity INTEGER NULL;

                COMMENT ON COLUMN equipment.equipments.quantity
                    IS '数量（台/套）';
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE equipment.equipments
            DROP COLUMN IF EXISTS quantity;
        """
    )
