"""0152_research_report_gen_opinion_library

研发报告生成的「意见库」与「生成前意见汇总」：

1. ``research.rd_report_gen_opinions``：跨报告/跨模板的全局意见库。原始意见仍记在
   ``rd_report_gen_feedback``（哪一版、谁提的），这里只存「可复用的规范化写法」：
   同一类意见反复出现时累计 ``hit_count``，而不是堆一堆近似重复的条目。
2. ``research.rd_report_gen_opinion_digests``：每次生成前 AI 把有效意见归并成的
   写作要求快照。为什么要留档：同一段汇总会被多条任务复用，出问题时必须能回答
   「这一版按哪份汇总写的、当时收了几条意见」。
3. ``research.rd_report_gen_jobs.opinion_digest_id``：任务到汇总快照的指针，
   详情页据此显示本次套用的汇总。

只动 research schema（单模块原则）；三张对象都没有历史数据需要回填。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa

from alembic import op

revision: str = "0152_research_report_gen_opinion_library"
down_revision: str | Sequence[str] | None = "0151_research_report_gen_manual_edit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "research"
_JOBS = "rd_report_gen_jobs"
_FEEDBACK = "rd_report_gen_feedback"
_OPINIONS = "rd_report_gen_opinions"
_DIGESTS = "rd_report_gen_opinion_digests"

_INDEX_JOB_DIGEST = "ix_research_rd_report_gen_jobs_digest"
_INDEX_OPINION_KEY = "ix_research_rd_report_gen_opinions_key"
_INDEX_OPINION_STATUS = "ix_research_rd_report_gen_opinions_status"
_INDEX_DIGEST_CREATED = "ix_research_rd_report_gen_opinion_digests_created"


def _base_columns() -> tuple[Any, ...]:
    """BaseModel 公共列：Column 不能挂到多张表上，每次建表都新建实例。"""
    return (
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=True),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), server_default="false", nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["identity.users.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["identity.users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def upgrade() -> None:
    op.create_table(
        _OPINIONS,
        *_base_columns(),
        sa.Column("content", sa.Text(), nullable=False, comment="规范化后的意见原文"),
        sa.Column(
            "normalized_key",
            sa.String(length=64),
            nullable=False,
            comment="归一化文本的 sha256，用于相同意见归并",
        ),
        sa.Column("hit_count", sa.Integer(), nullable=False, server_default="1", comment="被提出次数"),
        sa.Column(
            "status",
            sa.String(length=12),
            nullable=False,
            server_default="active",
            comment="active=参与汇总 / disabled=人工停用",
        ),
        sa.Column(
            "last_feedback_id",
            sa.Uuid(),
            nullable=True,
            comment="最近一次贡献该意见的原始记录（rd_report_gen_feedback）",
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True, comment="最近一次被提出时间"),
        sa.ForeignKeyConstraint(["last_feedback_id"], [f"{_SCHEMA}.{_FEEDBACK}.id"]),
        sa.CheckConstraint("status IN ('active', 'disabled')", name="ck_research_rd_report_gen_opinions_status"),
        sa.UniqueConstraint("normalized_key", name="uq_research_rd_report_gen_opinions_key"),
        schema=_SCHEMA,
        comment="AI 报告生成意见库（全局，跨报告归并）",
    )
    op.create_index(_INDEX_OPINION_KEY, _OPINIONS, ["normalized_key"], schema=_SCHEMA)
    op.create_index(_INDEX_OPINION_STATUS, _OPINIONS, ["status", "hit_count"], schema=_SCHEMA)

    op.create_table(
        _DIGESTS,
        *_base_columns(),
        sa.Column("digest_text", sa.Text(), nullable=False, comment="汇总后的写作要求（送进提示词的那段）"),
        sa.Column("item_count", sa.Integer(), nullable=False, server_default="0", comment="本次归并的意见条数"),
        sa.Column("opinion_ids", sa.JSON(), nullable=True, comment="参与汇总的意见 id 列表"),
        sa.Column("model_name", sa.String(length=128), nullable=True, comment="汇总所用模型"),
        sa.Column(
            "status",
            sa.String(length=12),
            nullable=False,
            server_default="ok",
            comment="ok=模型归并 / fallback=模型不可用退回原文清单",
        ),
        sa.Column("source_hash", sa.String(length=64), nullable=False, comment="意见集合指纹，便于判断汇总是否过期"),
        sa.CheckConstraint("status IN ('ok', 'fallback')", name="ck_research_rd_report_gen_opinion_digests_status"),
        schema=_SCHEMA,
        comment="AI 报告生成前的历史意见汇总快照",
    )
    op.create_index(_INDEX_DIGEST_CREATED, _DIGESTS, ["created_at"], schema=_SCHEMA)

    op.add_column(
        _JOBS,
        sa.Column(
            "opinion_digest_id",
            sa.Uuid(),
            nullable=True,
            comment="本次生成套用的历史意见汇总快照",
        ),
        schema=_SCHEMA,
    )
    op.create_foreign_key(
        "fk_research_rd_report_gen_jobs_digest",
        _JOBS,
        _DIGESTS,
        ["opinion_digest_id"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema=_SCHEMA,
    )
    op.create_index(_INDEX_JOB_DIGEST, _JOBS, ["opinion_digest_id"], schema=_SCHEMA)


def downgrade() -> None:
    op.drop_index(_INDEX_JOB_DIGEST, table_name=_JOBS, schema=_SCHEMA)
    op.drop_constraint("fk_research_rd_report_gen_jobs_digest", _JOBS, type_="foreignkey", schema=_SCHEMA)
    op.drop_column(_JOBS, "opinion_digest_id", schema=_SCHEMA)

    op.drop_index(_INDEX_DIGEST_CREATED, table_name=_DIGESTS, schema=_SCHEMA)
    op.drop_table(_DIGESTS, schema=_SCHEMA)

    op.drop_index(_INDEX_OPINION_STATUS, table_name=_OPINIONS, schema=_SCHEMA)
    op.drop_index(_INDEX_OPINION_KEY, table_name=_OPINIONS, schema=_SCHEMA)
    op.drop_table(_OPINIONS, schema=_SCHEMA)
