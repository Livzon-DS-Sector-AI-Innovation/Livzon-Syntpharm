"""add registration ledger tables

Revision ID: a1b2c3d4e5f7
Revises: xbj3_final_001
Create Date: 2026-06-25 10:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f7"
down_revision: str | None = "c7a8b9d0e1f2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 创建 registration schema（如果不存在）
    op.execute("CREATE SCHEMA IF NOT EXISTS registration")

    # 国内已获批品种表
    op.create_table(
        "registration_domestic_approvals",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("product_name", sa.String(255), nullable=False, comment="品名"),
        sa.Column(
            "certificate_name", sa.String(255), nullable=True, comment="证书名称"
        ),
        sa.Column(
            "batch_no", sa.String(128), nullable=True, comment="批件号（通知书编号）"
        ),
        sa.Column(
            "issuing_authority", sa.String(255), nullable=True, comment="国家/发证机关"
        ),
        sa.Column("issue_date", sa.Date, nullable=True, comment="发证日期"),
        sa.Column("valid_until", sa.Date, nullable=True, comment="证书有效期至"),
        sa.Column("product_scope", sa.Text, nullable=True, comment="产品范围"),
        sa.Column("quality_standard", sa.Text, nullable=True, comment="质量标准"),
        sa.Column("registration_no", sa.String(128), nullable=True, comment="登记号"),
        sa.Column("is_expired", sa.String(8), nullable=True, comment="证书是否过期"),
        sa.Column(
            "production_workshop", sa.String(255), nullable=True, comment="生产车间"
        ),
        sa.Column(
            "product_validity", sa.String(128), nullable=True, comment="产品有效期"
        ),
        sa.Column("storage_condition", sa.Text, nullable=True, comment="贮存条件"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.false()),
        schema="registration",
    )

    # 国外已获批品种表
    op.create_table(
        "registration_overseas_approvals",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("product_name", sa.String(255), nullable=False, comment="品名"),
        sa.Column(
            "certificate_name", sa.String(255), nullable=True, comment="证书名称"
        ),
        sa.Column(
            "batch_no", sa.String(128), nullable=True, comment="批件号（通知书编号）"
        ),
        sa.Column(
            "issuing_authority", sa.String(255), nullable=True, comment="国家/发证机关"
        ),
        sa.Column("issue_date", sa.Date, nullable=True, comment="发证日期"),
        sa.Column("valid_until", sa.Date, nullable=True, comment="证书有效期至"),
        sa.Column("product_scope", sa.Text, nullable=True, comment="产品范围"),
        sa.Column("quality_standard", sa.Text, nullable=True, comment="质量标准"),
        sa.Column("is_expired", sa.String(8), nullable=True, comment="证书是否过期"),
        sa.Column(
            "production_workshop", sa.String(255), nullable=True, comment="生产车间"
        ),
        sa.Column(
            "product_validity", sa.String(128), nullable=True, comment="产品有效期"
        ),
        sa.Column("storage_condition", sa.Text, nullable=True, comment="贮存条件"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.false()),
        schema="registration",
    )

    # 国际关联审评表
    op.create_table(
        "registration_international_reviews",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("product_name", sa.String(255), nullable=False, comment="品名"),
        sa.Column("approved_countries", sa.Text, nullable=True, comment="获批国家"),
        sa.Column(
            "approved_country_count", sa.Integer, nullable=True, comment="获批国家数量"
        ),
        sa.Column("approved_clients", sa.Text, nullable=True, comment="获批客户"),
        sa.Column(
            "approved_client_count", sa.Integer, nullable=True, comment="获批客户数量"
        ),
        sa.Column("reviewing_countries", sa.Text, nullable=True, comment="审评中-国家"),
        sa.Column(
            "reviewing_country_count",
            sa.Integer,
            nullable=True,
            comment="审评中-国家数量",
        ),
        sa.Column("reviewing_clients", sa.Text, nullable=True, comment="审评中-客户"),
        sa.Column(
            "reviewing_client_count",
            sa.Integer,
            nullable=True,
            comment="审评中-客户数量",
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.false()),
        schema="registration",
    )

    # COPP证书表
    op.create_table(
        "registration_copp_certificates",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("product_name", sa.String(255), nullable=False, comment="品名"),
        sa.Column(
            "certificate_name", sa.String(255), nullable=True, comment="证书名称"
        ),
        sa.Column(
            "batch_no", sa.String(128), nullable=True, comment="批件号（通知书编号）"
        ),
        sa.Column(
            "issuing_authority", sa.String(255), nullable=True, comment="国家/发证机关"
        ),
        sa.Column("issue_date", sa.Date, nullable=True, comment="发证日期"),
        sa.Column("valid_until", sa.Date, nullable=True, comment="证书有效期至"),
        sa.Column("product_scope", sa.Text, nullable=True, comment="产品范围"),
        sa.Column("applicable_countries", sa.Text, nullable=True, comment="适用国家"),
        sa.Column("is_expired", sa.String(8), nullable=True, comment="证书是否过期"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.false()),
        schema="registration",
    )

    # WC证书表
    op.create_table(
        "registration_wc_certificates",
        sa.Column(
            "id",
            sa.Uuid(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("product_name", sa.String(255), nullable=False, comment="品名"),
        sa.Column(
            "certificate_name", sa.String(255), nullable=True, comment="证书名称"
        ),
        sa.Column(
            "batch_no", sa.String(128), nullable=True, comment="批件号（通知书编号）"
        ),
        sa.Column(
            "issuing_authority", sa.String(255), nullable=True, comment="国家/发证机关"
        ),
        sa.Column("issue_date", sa.Date, nullable=True, comment="发证日期"),
        sa.Column("valid_until", sa.Date, nullable=True, comment="证书有效期至"),
        sa.Column("product_scope", sa.Text, nullable=True, comment="产品范围"),
        sa.Column("is_expired", sa.String(8), nullable=True, comment="证书是否过期"),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()
        ),
        sa.Column("created_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("updated_by", sa.Uuid(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, server_default=sa.false()),
        schema="registration",
    )


def downgrade() -> None:
    op.drop_table("registration_wc_certificates", schema="registration")
    op.drop_table("registration_copp_certificates", schema="registration")
    op.drop_table("registration_international_reviews", schema="registration")
    op.drop_table("registration_overseas_approvals", schema="registration")
    op.drop_table("registration_domestic_approvals", schema="registration")
