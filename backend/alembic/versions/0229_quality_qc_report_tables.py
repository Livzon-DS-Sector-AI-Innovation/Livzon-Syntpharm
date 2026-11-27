"""create quality qc report tables

Revision ID: 0229_quality_qc_report_tables
Revises: 0228_registration_project_owner_id
Create Date: 2026-11-26

「检验管理 > 质量检验」从零建设检验台账，本期新建 4 张表（quality schema）：

- qc_products：品种（名称、缩写、物料分类、质量标准）
- qc_items：检验项目，三层标准（法定 / 企业内控 / 3σ）以原文文本保存，不拆上下限
- qc_batches：批次，batch_no 用文本保留 QS22601001 这类前导字母
- qc_values：批次 × 项目 的实测值与判定等级

唯一性约束均采用「仅未软删行唯一」的部分唯一索引，软删后可重建同名记录。
与 CPV、检验标准完全独立，不复用其表结构。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0229_quality_qc_report_tables"
down_revision: str | None = "0228_registration_project_owner_id"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "quality"
_NOT_DELETED = sa.text("is_deleted = false")


def _audit_columns() -> list[sa.Column]:
    """BaseModel 的公共列。"""
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    ]


def upgrade() -> None:
    op.create_table(
        "qc_products",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False, comment="品种名称"),
        sa.Column("abbr", sa.String(16), nullable=False, comment="品名缩写（批号前缀，未软删行内唯一）"),
        sa.Column("category", sa.String(32), nullable=False, comment="物料分类：raw/intermediate/finished"),
        sa.Column("quality_standard", sa.String(255), nullable=True, comment="质量标准（药典版本/标准编号）"),
        sa.Column("source_file_name", sa.String(255), nullable=True, comment="导入所用的结果表文件名"),
        sa.Column("status", sa.String(20), server_default="active", nullable=False, comment="状态：active/inactive"),
        sa.Column("last_inspected_at", sa.DateTime(timezone=True), nullable=True, comment="最近一次录入/导入批次的时间"),
        *_audit_columns(),
        schema=_SCHEMA,
        comment="质量检验-品种",
    )
    op.create_index(
        "uq_qc_products_abbr",
        "qc_products",
        ["abbr"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=_NOT_DELETED,
    )
    op.create_index("ix_qc_products_category", "qc_products", ["category"], schema=_SCHEMA)

    op.create_table(
        "qc_items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("quality.qc_products.id"),
            nullable=False,
            comment="品种ID",
        ),
        sa.Column("item_no", sa.Integer(), server_default="0", nullable=False, comment="顺序号（= Excel 列号）"),
        sa.Column("item_name", sa.String(200), nullable=False, comment="项目名（取 Excel 表头原文，合并组内多列同名）"),
        sa.Column(
            "value_type",
            sa.String(16),
            server_default="quant",
            nullable=False,
            comment="项目类型：quant 数值 / qual 文字 / grade 等级型",
        ),
        sa.Column("unit", sa.String(32), nullable=True, comment="单位"),
        sa.Column("legal_text", sa.Text(), nullable=True, comment="法定标准原文"),
        sa.Column("internal_text", sa.Text(), nullable=True, comment="企业内控标准原文"),
        sa.Column("sigma_text", sa.String(255), nullable=True, comment="3σ 标准原文"),
        sa.Column("source_column", sa.String(200), nullable=True, comment="对应结果表的列标识（列号或列名），用于再次导入时自动套用"),
        sa.Column(
            "is_record_only",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="仅记录不判定（结果表有、标准表没有的列）",
        ),
        sa.Column("sigma_basis_period", sa.String(32), nullable=True, comment="3σ 基准期，如 2025 年度"),
        sa.Column(
            "sigma_updated_by",
            UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=True,
            comment="3σ 最近更新人",
        ),
        sa.Column("sigma_updated_at", sa.DateTime(timezone=True), nullable=True, comment="3σ 最近更新时间"),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False, comment="展示排序"),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False, comment="是否启用"),
        *_audit_columns(),
        schema=_SCHEMA,
        comment="质量检验-检验项目",
    )
    op.create_index("ix_qc_items_product", "qc_items", ["product_id"], schema=_SCHEMA)
    op.create_index(
        "uq_qc_items_product_name",
        "qc_items",
        ["product_id", "item_name"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=_NOT_DELETED,
    )

    op.create_table(
        "qc_batches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "product_id",
            UUID(as_uuid=True),
            sa.ForeignKey("quality.qc_products.id"),
            nullable=False,
            comment="品种ID",
        ),
        sa.Column("batch_no", sa.String(64), nullable=False, comment="批号（文本，保留前导字母）"),
        sa.Column(
            "level",
            sa.String(16),
            server_default="pending",
            nullable=False,
            comment="整批最高等级：oos/internal/trend/normal/skip/pending",
        ),
        sa.Column("note", sa.Text(), nullable=True, comment="备注"),
        sa.Column("entered_by_name", sa.String(100), nullable=True, comment="录入人姓名快照"),
        sa.Column(
            "source",
            sa.String(16),
            server_default="import",
            nullable=False,
            comment="来源：import/manual",
        ),
        *_audit_columns(),
        schema=_SCHEMA,
        comment="质量检验-批次",
    )
    op.create_index("ix_qc_batches_product", "qc_batches", ["product_id"], schema=_SCHEMA)
    op.create_index(
        "ix_qc_batches_product_level",
        "qc_batches",
        ["product_id", "level"],
        schema=_SCHEMA,
    )
    op.create_index(
        "uq_qc_batches_product_batch",
        "qc_batches",
        ["product_id", "batch_no"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=_NOT_DELETED,
    )

    op.create_table(
        "qc_values",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "batch_id",
            UUID(as_uuid=True),
            sa.ForeignKey("quality.qc_batches.id"),
            nullable=False,
            comment="批次ID",
        ),
        sa.Column(
            "item_id",
            UUID(as_uuid=True),
            sa.ForeignKey("quality.qc_items.id"),
            nullable=False,
            comment="项目ID",
        ),
        sa.Column("actual_value", sa.String(255), nullable=True, comment="实测值原文（兼容「符合规定」「未检出」等文字）"),
        sa.Column("numeric_value", sa.Numeric(18, 6), nullable=True, comment="实测值数值化结果，供比较与聚合"),
        sa.Column(
            "level",
            sa.String(16),
            server_default="pending",
            nullable=False,
            comment="本格判定：oos/internal/trend/normal/skip/pending",
        ),
        *_audit_columns(),
        schema=_SCHEMA,
        comment="质量检验-实测值",
    )
    op.create_index("ix_qc_values_batch", "qc_values", ["batch_id"], schema=_SCHEMA)
    op.create_index("ix_qc_values_item", "qc_values", ["item_id"], schema=_SCHEMA)
    op.create_index(
        "uq_qc_values_batch_item",
        "qc_values",
        ["batch_id", "item_id"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=_NOT_DELETED,
    )


def downgrade() -> None:
    op.drop_index("uq_qc_values_batch_item", "qc_values", schema=_SCHEMA, postgresql_where=_NOT_DELETED)
    op.drop_index("ix_qc_values_item", "qc_values", schema=_SCHEMA)
    op.drop_index("ix_qc_values_batch", "qc_values", schema=_SCHEMA)
    op.drop_table("qc_values", schema=_SCHEMA)

    op.drop_index("uq_qc_batches_product_batch", "qc_batches", schema=_SCHEMA, postgresql_where=_NOT_DELETED)
    op.drop_index("ix_qc_batches_product_level", "qc_batches", schema=_SCHEMA)
    op.drop_index("ix_qc_batches_product", "qc_batches", schema=_SCHEMA)
    op.drop_table("qc_batches", schema=_SCHEMA)

    op.drop_index("uq_qc_items_product_name", "qc_items", schema=_SCHEMA, postgresql_where=_NOT_DELETED)
    op.drop_index("ix_qc_items_product", "qc_items", schema=_SCHEMA)
    op.drop_table("qc_items", schema=_SCHEMA)

    op.drop_index("ix_qc_products_category", "qc_products", schema=_SCHEMA)
    op.drop_index("uq_qc_products_abbr", "qc_products", schema=_SCHEMA, postgresql_where=_NOT_DELETED)
    op.drop_table("qc_products", schema=_SCHEMA)
