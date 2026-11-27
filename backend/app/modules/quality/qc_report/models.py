"""质量检验台账 ORM 模型：品种 / 检验项目 / 批次 / 数值。

与 CPV、检验标准完全独立：标准表 docx 是标准的唯一来源，
结果表 xlsx 只提供批号与实测数据。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.shared.base_model import BaseModel

_SCHEMA = "quality"


class QcProduct(BaseModel):
    """检验台账品种（一个品种一条）。"""

    __tablename__ = "qc_products"
    __table_args__ = (
        # 缩写唯一，仅约束未软删行
        Index(
            "uq_qc_products_abbr",
            "abbr",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        Index("ix_qc_products_category", "category"),
        {"schema": _SCHEMA, "comment": "质量检验-品种"},
    )

    name: Mapped[str] = mapped_column(String(200), nullable=False, comment="品种名称")
    abbr: Mapped[str] = mapped_column(String(16), nullable=False, comment="品名缩写（批号前缀，未软删行内唯一）")
    category: Mapped[str] = mapped_column(String(32), nullable=False, comment="物料分类：raw/intermediate/finished")
    quality_standard: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="质量标准（药典版本/标准编号）"
    )
    source_file_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="导入所用的结果表文件名")
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="active", server_default="active", comment="状态：active/inactive"
    )
    last_inspected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="最近一次录入/导入批次的时间"
    )

    items: Mapped[list[QcItem]] = relationship("QcItem", back_populates="product", cascade="all, delete-orphan")


class QcItem(BaseModel):
    """检验项目（一个品种多个项目），三层标准以原文文本保存。"""

    __tablename__ = "qc_items"
    __table_args__ = (
        Index("ix_qc_items_product", "product_id"),
        # 同名项目是合法的：可见异物初检横跨 4 列同名、不溶性微粒两列也同名。
        # 因此唯一性从「项目名」改为「列位」——sort_order 即 Excel 列号，
        # 既允许重名，又把「第几列」锁死，任何重排都会在数据库层被拦住。
        Index(
            "uq_qc_items_product_order",
            "product_id",
            "sort_order",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"schema": _SCHEMA, "comment": "质量检验-检验项目"},
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quality.qc_products.id"), nullable=False, comment="品种ID"
    )
    item_no: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="顺序号（= Excel 列号）")
    item_name: Mapped[str] = mapped_column(
        String(200), nullable=False, comment="项目名（取 Excel 表头原文，合并组内多列同名）"
    )
    standard_item_name: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="标准表原始项目名，用于追溯限值来源"
    )
    standard_source: Mapped[str | None] = mapped_column(
        String(16),
        nullable=True,
        comment="本列三层标准取自哪份文件：excel 结果表 / docx 标准表 / none 人工留空 / mixed 各层不同",
    )
    column_group_start: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="所属表头组的首列列号，合并表头据此跨列渲染"
    )
    sub_label: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="合并组内续列的子列名，如 毛 / 点（总数≤5个）/ 备注"
    )
    value_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="quant",
        server_default="quant",
        comment="项目类型：quant 数值 / qual 文字 / grade 等级型",
    )
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="单位")

    legal_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="法定标准原文")
    internal_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="企业内控标准原文")
    sigma_text: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="3σ 标准原文")

    source_column: Mapped[str | None] = mapped_column(
        String(200), nullable=True, comment="对应结果表的列标识（列号或列名），用于再次导入时自动套用"
    )
    is_record_only: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="仅记录不判定（结果表有、标准表没有的列）",
    )

    sigma_basis_period: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="3σ 基准期，如 2025 年度")
    sigma_updated_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("identity.users.id"), nullable=True, comment="3σ 最近更新人"
    )
    sigma_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="3σ 最近更新时间"
    )

    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="展示排序")
    is_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true", comment="是否启用"
    )

    product: Mapped[QcProduct] = relationship("QcProduct", back_populates="items")


class QcBatch(BaseModel):
    """检验批次（一行一个批号），level 为整批最高风险等级。"""

    __tablename__ = "qc_batches"
    __table_args__ = (
        Index("ix_qc_batches_product", "product_id"),
        Index("ix_qc_batches_product_level", "product_id", "level"),
        Index(
            "uq_qc_batches_product_batch",
            "product_id",
            "batch_no",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"schema": _SCHEMA, "comment": "质量检验-批次"},
    )

    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("quality.qc_products.id"), nullable=False, comment="品种ID"
    )
    batch_no: Mapped[str] = mapped_column(String(64), nullable=False, comment="批号（文本，保留前导字母）")
    level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="整批最高等级：oos/internal/trend/normal/skip/pending",
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")
    entered_by_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="录入人姓名快照")
    source: Mapped[str] = mapped_column(
        String(16), nullable=False, default="import", server_default="import", comment="来源：import/manual"
    )


class QcValue(BaseModel):
    """批次 × 项目 的实测值与判定结果。"""

    __tablename__ = "qc_values"
    __table_args__ = (
        Index("ix_qc_values_batch", "batch_id"),
        Index("ix_qc_values_item", "item_id"),
        Index(
            "uq_qc_values_batch_item",
            "batch_id",
            "item_id",
            unique=True,
            postgresql_where=text("is_deleted = false"),
        ),
        {"schema": _SCHEMA, "comment": "质量检验-实测值"},
    )

    batch_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quality.qc_batches.id"), nullable=False, comment="批次ID")
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("quality.qc_items.id"), nullable=False, comment="项目ID")
    actual_value: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="实测值原文（兼容「符合规定」「未检出」等文字）"
    )
    numeric_value: Mapped[Decimal | None] = mapped_column(
        Numeric(18, 6), nullable=True, comment="实测值数值化结果，供比较与聚合"
    )
    level: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="pending",
        server_default="pending",
        comment="本格判定：oos/internal/trend/normal/skip/pending",
    )


__all__ = ["QcProduct", "QcItem", "QcBatch", "QcValue"]
