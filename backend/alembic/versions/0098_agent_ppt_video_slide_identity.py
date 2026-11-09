"""split slide identity from slide number

Revision ID: 0098_agent_ppt_video_slide_identity
Revises: 0097_llm_config_owner_scope
Create Date: 2026-11-03

换源后页序会整体平移，而 `slide_no` 过去同时承担「页码」和「身份」两个职责：

- 唯一约束 (project_id, slide_no) 让页码无法在事务内整体平移；
- 页图对象 key 用 slide_no，插页后新页会覆盖旧页图片。

本次迁移只做结构拆分，**不改变任何行为**：

- project：llm_config_id / script_guide / source_version
- slide  ：slide_uid（稳定身份）/ source_index（源 PPT 页序）/ page_fingerprint / layout / script_stale
- 约束  ：(project_id, slide_no) 改为 DEFERRABLE INITIALLY DEFERRED，另加 (project_id, slide_uid) 唯一
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0098_agent_ppt_video_slide_identity"
down_revision: str = "0097_llm_config_owner_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = :schema AND table_name = :table AND column_name = :column
            """
        ),
        {"schema": SCHEMA, "table": table_name, "column": column_name},
    )
    return result.scalar() is not None


def _constraint_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(
        sa.text(
            """
            SELECT 1
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE n.nspname = :schema AND t.relname = :table AND c.conname = :name
            """
        ),
        {"schema": SCHEMA, "table": table_name, "name": constraint_name},
    )
    return result.scalar() is not None


def upgrade() -> None:
    # ── project ────────────────────────────────────────────────
    project_columns = (
        sa.Column(
            "llm_config_id",
            sa.UUID(as_uuid=True),
            nullable=True,
            comment="项目级模型覆盖（core.llm_configs.id）；空=跟随全局默认",
        ),
        sa.Column("script_guide", sa.Text(), nullable=True, comment="项目级讲稿风格指南；空=继承全局"),
        sa.Column(
            "source_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
            comment="源 PPT 版本号，对象 key 为 source-v{n}.pptx",
        ),
    )
    for column in project_columns:
        if not _column_exists("ppt_video_project", column.name):
            op.add_column("ppt_video_project", column, schema=SCHEMA)

    # ── slide 身份拆分 ─────────────────────────────────────────
    if not _column_exists("ppt_video_slide", "slide_uid"):
        op.add_column(
            "ppt_video_slide",
            sa.Column(
                "slide_uid",
                sa.UUID(as_uuid=True),
                nullable=True,
                comment="稳定身份：换源对齐、讲稿/音频/页图归属都挂在它上面",
            ),
            schema=SCHEMA,
        )
        op.execute(sa.text(f"UPDATE {SCHEMA}.ppt_video_slide SET slide_uid = gen_random_uuid() WHERE slide_uid IS NULL"))
        op.alter_column("ppt_video_slide", "slide_uid", nullable=False, schema=SCHEMA)

    if not _column_exists("ppt_video_slide", "source_index"):
        op.add_column(
            "ppt_video_slide",
            sa.Column(
                "source_index",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="当前源 PPT 中的页序（1 起）",
            ),
            schema=SCHEMA,
        )
        op.execute(sa.text(f"UPDATE {SCHEMA}.ppt_video_slide SET source_index = slide_no"))
        op.alter_column("ppt_video_slide", "source_index", server_default="0", schema=SCHEMA)

    if not _column_exists("ppt_video_slide", "page_fingerprint"):
        op.add_column(
            "ppt_video_slide",
            sa.Column(
                "page_fingerprint",
                sa.String(length=64),
                nullable=True,
                comment="页内容指纹（文字+备注+形状数+坐标摘要），用于换源对齐",
            ),
            schema=SCHEMA,
        )
    if not _column_exists("ppt_video_slide", "layout"):
        op.add_column(
            "ppt_video_slide",
            sa.Column("layout", sa.JSON(), nullable=True, comment="形状坐标清单（EMU）"),
            schema=SCHEMA,
        )
    if not _column_exists("ppt_video_slide", "script_stale"):
        op.add_column(
            "ppt_video_slide",
            sa.Column(
                "script_stale",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="画面已变、讲稿尚未按新画面重写",
            ),
            schema=SCHEMA,
        )

    # ── 约束改造 ───────────────────────────────────────────────
    if _constraint_exists("ppt_video_slide", "uq_agent_ppt_video_slide_project_no"):
        op.drop_constraint("uq_agent_ppt_video_slide_project_no", "ppt_video_slide", schema=SCHEMA, type_="unique")
    op.execute(
        sa.text(
            f"ALTER TABLE {SCHEMA}.ppt_video_slide "
            f"ADD CONSTRAINT uq_agent_ppt_video_slide_project_no "
            f"UNIQUE (project_id, slide_no) DEFERRABLE INITIALLY DEFERRED"
        )
    )

    if not _constraint_exists("ppt_video_slide", "uq_agent_ppt_video_slide_project_uid"):
        op.create_unique_constraint(
            "uq_agent_ppt_video_slide_project_uid", "ppt_video_slide", ["project_id", "slide_uid"], schema=SCHEMA
        )


def downgrade() -> None:
    if _constraint_exists("ppt_video_slide", "uq_agent_ppt_video_slide_project_uid"):
        op.drop_constraint("uq_agent_ppt_video_slide_project_uid", "ppt_video_slide", schema=SCHEMA, type_="unique")

    if _constraint_exists("ppt_video_slide", "uq_agent_ppt_video_slide_project_no"):
        op.drop_constraint("uq_agent_ppt_video_slide_project_no", "ppt_video_slide", schema=SCHEMA, type_="unique")
    op.execute(
        sa.text(
            f"ALTER TABLE {SCHEMA}.ppt_video_slide "
            f"ADD CONSTRAINT uq_agent_ppt_video_slide_project_no UNIQUE (project_id, slide_no)"
        )
    )

    for column_name in ("script_stale", "layout", "page_fingerprint", "source_index", "slide_uid"):
        if _column_exists("ppt_video_slide", column_name):
            op.drop_column("ppt_video_slide", column_name, schema=SCHEMA)

    for column_name in ("source_version", "script_guide", "llm_config_id"):
        if _column_exists("ppt_video_project", column_name):
            op.drop_column("ppt_video_project", column_name, schema=SCHEMA)