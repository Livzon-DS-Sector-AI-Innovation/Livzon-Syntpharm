"""sync agent ppt video column comments and audit foreign keys

Revision ID: 0142_agent_ppt_video_column_comments_and_audit_fk
Revises: 0141_merge_main_and_agent_ppt_video_heads
Create Date: 2026-11-18

建表后模型注释经过多轮迭代（页面页码语义、段级讲稿兜底规则、高亮覆盖层级从模块改为项目等），
数据库里的列注释仍是初版文案；同时 `ppt_video_script_revision` 的审计列在建表时漏掉了
到 `identity.users` 的外键。本迁移把库侧对齐到当前模型，避免 `alembic check` 长期漂移。

仅改注释与两个外键，不动数据；仅涉及 agent schema（外键引用 identity.users 属允许的跨模块引用）。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0142_agent_ppt_video_column_comments_and_audit_fk"
down_revision: str = "0141_merge_main_and_agent_ppt_video_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"
FK_CREATED_BY = "fk_ppt_video_script_revision_created_by_users"
FK_UPDATED_BY = "fk_ppt_video_script_revision_updated_by_users"


def upgrade() -> None:
    op.alter_column(
        "ppt_video_job",
        "stage",
        existing_type=sa.VARCHAR(length=32),
        comment="queued/parse/render/tts/concat/upload",
        existing_comment="阶段: queued/parse/render/tts/concat/upload",
        existing_nullable=False,
        existing_server_default=sa.text("'queued'::character varying"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_job",
        "max_attempts",
        existing_type=sa.INTEGER(),
        comment="重试上限",
        existing_comment="最大尝试次数",
        existing_nullable=False,
        existing_server_default=sa.text("3"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_project",
        "slide_count",
        existing_type=sa.INTEGER(),
        comment="页数",
        existing_comment="幻灯片页数",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "before",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="改写前快照 {slide_uid: text}",
        existing_comment="改写前讲稿快照 {slide_uid: text}",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "after",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="改写后快照 {slide_uid: text}",
        existing_comment="改写后讲稿快照 {slide_uid: text}",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "applied",
        existing_type=sa.BOOLEAN(),
        comment="是否仍生效；回滚后置 false",
        existing_comment="是否仍生效",
        existing_nullable=False,
        existing_server_default=sa.text("true"),
        schema=SCHEMA,
    )
    op.create_foreign_key(
        FK_CREATED_BY,
        "ppt_video_script_revision",
        "users",
        ["created_by"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema="identity",
    )
    op.create_foreign_key(
        FK_UPDATED_BY,
        "ppt_video_script_revision",
        "users",
        ["updated_by"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema="identity",
    )
    op.alter_column(
        "ppt_video_segment",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="片段时长",
        existing_comment="片段时长(ms)",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "slide_no",
        existing_type=sa.INTEGER(),
        comment="展示页码，从 1 开始，换源后会重排",
        existing_comment="页码，从 1 开始",
        existing_nullable=False,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "script_segments",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text，否则视为已手改、按字面兜底",
        existing_comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_style",
        existing_type=sa.VARCHAR(length=16),
        comment="覆盖本页视觉引导样式；空=用项目设置",
        existing_comment="覆盖本页视觉引导样式；空=用模块设置",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_color",
        existing_type=sa.VARCHAR(length=16),
        comment="覆盖本页高亮主色 #RRGGBB；空=用项目设置",
        existing_comment="覆盖本页高亮主色 #RRGGBB；空=用模块设置",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_regions",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="区域级高亮配置 {regions,sentences}；空=按讲稿自动判定",
        existing_comment="区域级高亮配置 {regions[],sentences[]}；空=按讲稿自动判定",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "audio_object_key",
        existing_type=sa.VARCHAR(length=512),
        comment="旁白 wav 对象路径",
        existing_comment="旁白 wav 的 MinIO 对象路径",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="旁白时长",
        existing_comment="旁白时长(ms)",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "layout",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="页版式：{width,height,shapes[]} 字典或裸形状列表（EMU）",
        existing_comment="形状坐标清单（EMU）",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_version",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="成片时长",
        existing_comment="成片时长(ms)",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_version",
        "manifest",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="复用取证清单",
        existing_comment="复用取证清单（每页 sha256 与命中情况）",
        existing_nullable=False,
        schema=SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        "ppt_video_version",
        "manifest",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="复用取证清单（每页 sha256 与命中情况）",
        existing_comment="复用取证清单",
        existing_nullable=False,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_version",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="成片时长(ms)",
        existing_comment="成片时长",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "layout",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="形状坐标清单（EMU）",
        existing_comment="页版式：{width,height,shapes[]} 字典或裸形状列表（EMU）",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="旁白时长(ms)",
        existing_comment="旁白时长",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "audio_object_key",
        existing_type=sa.VARCHAR(length=512),
        comment="旁白 wav 的 MinIO 对象路径",
        existing_comment="旁白 wav 对象路径",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_regions",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="区域级高亮配置 {regions[],sentences[]}；空=按讲稿自动判定",
        existing_comment="区域级高亮配置 {regions,sentences}；空=按讲稿自动判定",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_color",
        existing_type=sa.VARCHAR(length=16),
        comment="覆盖本页高亮主色 #RRGGBB；空=用模块设置",
        existing_comment="覆盖本页高亮主色 #RRGGBB；空=用项目设置",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_style",
        existing_type=sa.VARCHAR(length=16),
        comment="覆盖本页视觉引导样式；空=用模块设置",
        existing_comment="覆盖本页视觉引导样式；空=用项目设置",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "script_segments",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text",
        existing_comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text，否则视为已手改、按字面兜底",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "slide_no",
        existing_type=sa.INTEGER(),
        comment="页码，从 1 开始",
        existing_comment="展示页码，从 1 开始，换源后会重排",
        existing_nullable=False,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_segment",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="片段时长(ms)",
        existing_comment="片段时长",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=SCHEMA,
    )
    op.drop_constraint(FK_UPDATED_BY, "ppt_video_script_revision", schema=SCHEMA, type_="foreignkey")
    op.drop_constraint(FK_CREATED_BY, "ppt_video_script_revision", schema=SCHEMA, type_="foreignkey")
    op.alter_column(
        "ppt_video_script_revision",
        "applied",
        existing_type=sa.BOOLEAN(),
        comment="是否仍生效",
        existing_comment="是否仍生效；回滚后置 false",
        existing_nullable=False,
        existing_server_default=sa.text("true"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "after",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="改写后讲稿快照 {slide_uid: text}",
        existing_comment="改写后快照 {slide_uid: text}",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "before",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="改写前讲稿快照 {slide_uid: text}",
        existing_comment="改写前快照 {slide_uid: text}",
        existing_nullable=True,
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_project",
        "slide_count",
        existing_type=sa.INTEGER(),
        comment="幻灯片页数",
        existing_comment="页数",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_job",
        "max_attempts",
        existing_type=sa.INTEGER(),
        comment="最大尝试次数",
        existing_comment="重试上限",
        existing_nullable=False,
        existing_server_default=sa.text("3"),
        schema=SCHEMA,
    )
    op.alter_column(
        "ppt_video_job",
        "stage",
        existing_type=sa.VARCHAR(length=32),
        comment="阶段: queued/parse/render/tts/concat/upload",
        existing_comment="queued/parse/render/tts/concat/upload",
        existing_nullable=False,
        existing_server_default=sa.text("'queued'::character varying"),
        schema=SCHEMA,
    )