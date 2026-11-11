"""add quality deviation ledger

Revision ID: 0101_add_quality_deviation_ledger
Revises: 0100_safety_equipment_facility_hazards
Create Date: 2026-11-10

新增《偏差台账》主表 quality.deviation_ledger，字段按妙搭偏差主表素化对齐。
不动旧表 quality.quality_deviations（14 态流程模型），只动 quality schema，单模块迁移。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision: str = "0101_add_quality_deviation_ledger"
down_revision: str = "0100_safety_equipment_facility_hazards"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "deviation_ledger"
_SCHEMA = "quality"

_STATUSES = (
    "draft",
    "pending_ai_analysis",
    "pending_investigation",
    "pending_dept_head_review",
    "pending_cross_dept_head_review",
    "pending_qa_review",
    "pending_qa_head_review",
    "pending_quality_head_review",
    "pending_final_code",
    "returned",
    "closed",
    "cancelled",
)
_LEVELS = ("minor", "moderate", "major")

_STATUS_IN = ", ".join(f"'{value}'" for value in _STATUSES)
_LEVEL_IN = ", ".join(f"'{value}'" for value in _LEVELS)


def upgrade() -> None:
    op.create_table(
        _TABLE,
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(32), nullable=False, comment="系统编号 PC+YYYYMMDD+3位序号"),
        sa.Column("final_code", sa.String(32), nullable=True, comment="最终编号（台账优先显示）"),
        sa.Column("title", sa.String(255), nullable=False, comment="偏差标题"),
        sa.Column("department", sa.String(255), nullable=False, comment="所属部门（=发生部门）"),
        sa.Column("discovery_date", sa.Date(), nullable=False, comment="发现日期"),
        sa.Column("discovery_time", sa.String(8), nullable=True, comment="发现时间 HH:MM"),
        sa.Column("discovery_location", sa.String(255), nullable=False, comment="发现地点"),
        sa.Column(
            "discoverer_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
            comment="发现人（默认当前登录人）",
        ),
        sa.Column("affected_items", sa.Text(), nullable=False, comment="受影响的产品/物料/设备/仪器"),
        sa.Column("batch_number", sa.String(255), nullable=False, comment="批号/位号/编号"),
        sa.Column("description", sa.Text(), nullable=False, comment="偏差描述"),
        sa.Column(
            "status",
            sa.String(40),
            nullable=False,
            server_default=sa.text("'pending_ai_analysis'"),
            comment="状态（12 态）",
        ),
        sa.Column("returned_step", sa.String(40), nullable=True, comment="退回时所在环节"),
        sa.Column(
            "status_updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="状态变更时间（超期判定基准）",
        ),
        sa.Column("deviation_level", sa.String(20), nullable=True, comment="分级 minor/moderate/major"),
        sa.Column("reason_category", sa.String(50), nullable=True, comment="原因分类"),
        sa.Column(
            "reporter_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("identity.users.id"),
            nullable=False,
            comment="上报人（创建人）",
        ),
        sa.Column("handler_ids", ARRAY(PG_UUID(as_uuid=True)), nullable=True, comment="调查人（可多人）"),
        sa.Column(
            "needs_cross_dept_review",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="是否需要跨部门审核",
        ),
        sa.Column(
            "cross_dept_reviewers",
            JSONB(),
            nullable=True,
            comment="跨部门调查人 [{department, investigators[]}]",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", PG_UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("updated_by", PG_UUID(as_uuid=True), sa.ForeignKey("identity.users.id"), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.CheckConstraint(f"status IN ({_STATUS_IN})", name="ck_deviation_ledger_status"),
        sa.CheckConstraint(
            f"deviation_level IS NULL OR deviation_level IN ({_LEVEL_IN})",
            name="ck_deviation_ledger_level",
        ),
        schema=_SCHEMA,
    )
    op.create_index("uq_deviation_ledger_code", _TABLE, ["code"], unique=True, schema=_SCHEMA)
    op.create_index(
        "uq_deviation_ledger_final_code",
        _TABLE,
        ["final_code"],
        unique=True,
        schema=_SCHEMA,
        postgresql_where=sa.text("final_code IS NOT NULL AND is_deleted = false"),
    )
    op.create_index("ix_deviation_ledger_status", _TABLE, ["status"], schema=_SCHEMA)
    op.create_index("ix_deviation_ledger_department", _TABLE, ["department"], schema=_SCHEMA)
    op.create_index("ix_deviation_ledger_discovery_date", _TABLE, ["discovery_date"], schema=_SCHEMA)
    op.create_index("ix_deviation_ledger_created_at", _TABLE, ["created_at"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index("ix_deviation_ledger_created_at", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("ix_deviation_ledger_discovery_date", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("ix_deviation_ledger_department", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("ix_deviation_ledger_status", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("uq_deviation_ledger_final_code", table_name=_TABLE, schema=_SCHEMA)
    op.drop_index("uq_deviation_ledger_code", table_name=_TABLE, schema=_SCHEMA)
    op.drop_table(_TABLE, schema=_SCHEMA)
