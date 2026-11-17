"""align agent ppt_video drift

Revision ID: 0189_align_agent_ppt_video_drift
Revises: 0188_merge_feature_and_uat_mainline
Create Date: 2026-11-16

对齐 uat 链遗留的模型/迁移漂移（双轨合并时随 uat 主链引入，autogenerate 生成后人工整理）：

- agent.ppt_video_* 列注释同步为模型当前文本；
- agent.ppt_video_script_revision 补上模型已声明但库中缺失的 created_by/updated_by 外键。

仅注释与外键，不涉及类型或约束变更，只动 agent schema。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0189_align_agent_ppt_video_drift"
down_revision: str = "0188_merge_feature_and_uat_mainline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SCHEMA = "agent"
_FK_CREATED = "ppt_video_script_revision_created_by_fkey"
_FK_UPDATED = "ppt_video_script_revision_updated_by_fkey"


def upgrade() -> None:
    op.alter_column(
        "ppt_video_job",
        "stage",
        existing_type=sa.VARCHAR(length=32),
        comment="queued/parse/render/tts/concat/upload",
        existing_comment="阶段: queued/parse/render/tts/concat/upload",
        existing_nullable=False,
        existing_server_default=sa.text("'queued'::character varying"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_job",
        "max_attempts",
        existing_type=sa.INTEGER(),
        comment="重试上限",
        existing_comment="最大尝试次数",
        existing_nullable=False,
        existing_server_default=sa.text("3"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_project",
        "slide_count",
        existing_type=sa.INTEGER(),
        comment="页数",
        existing_comment="幻灯片页数",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "before",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="改写前快照 {slide_uid: text}",
        existing_comment="改写前讲稿快照 {slide_uid: text}",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "after",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="改写后快照 {slide_uid: text}",
        existing_comment="改写后讲稿快照 {slide_uid: text}",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "applied",
        existing_type=sa.BOOLEAN(),
        comment="是否仍生效；回滚后置 false",
        existing_comment="是否仍生效",
        existing_nullable=False,
        existing_server_default=sa.text("true"),
        schema=_SCHEMA,
    )
    op.create_foreign_key(
        _FK_UPDATED,
        "ppt_video_script_revision",
        "users",
        ["updated_by"],
        ["id"],
        source_schema=_SCHEMA,
        referent_schema="identity",
    )
    op.create_foreign_key(
        _FK_CREATED,
        "ppt_video_script_revision",
        "users",
        ["created_by"],
        ["id"],
        source_schema=_SCHEMA,
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
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "slide_no",
        existing_type=sa.INTEGER(),
        comment="展示页码，从 1 开始，换源后会重排",
        existing_comment="页码，从 1 开始",
        existing_nullable=False,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "script_segments",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text，否则视为已手改、按字面兜底",
        existing_comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_style",
        existing_type=sa.VARCHAR(length=16),
        comment="覆盖本页视觉引导样式；空=用项目设置",
        existing_comment="覆盖本页视觉引导样式；空=用模块设置",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_color",
        existing_type=sa.VARCHAR(length=16),
        comment="覆盖本页高亮主色 #RRGGBB；空=用项目设置",
        existing_comment="覆盖本页高亮主色 #RRGGBB；空=用模块设置",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_regions",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="区域级高亮配置 {regions,sentences}；空=按讲稿自动判定",
        existing_comment="区域级高亮配置 {regions[],sentences[]}；空=按讲稿自动判定",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "audio_object_key",
        existing_type=sa.VARCHAR(length=512),
        comment="旁白 wav 对象路径",
        existing_comment="旁白 wav 的 MinIO 对象路径",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="旁白时长",
        existing_comment="旁白时长(ms)",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "layout",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="页版式：{width,height,shapes[]} 字典或裸形状列表（EMU）",
        existing_comment="形状坐标清单（EMU）",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_version",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="成片时长",
        existing_comment="成片时长(ms)",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_version",
        "manifest",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="复用取证清单",
        existing_comment="复用取证清单（每页 sha256 与命中情况）",
        existing_nullable=False,
        schema=_SCHEMA,
    )


def downgrade() -> None:
    op.alter_column(
        "ppt_video_version",
        "manifest",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="复用取证清单（每页 sha256 与命中情况）",
        existing_comment="复用取证清单",
        existing_nullable=False,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_version",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="成片时长(ms)",
        existing_comment="成片时长",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "layout",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="形状坐标清单（EMU）",
        existing_comment="页版式：{width,height,shapes[]} 字典或裸形状列表（EMU）",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="旁白时长(ms)",
        existing_comment="旁白时长",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "audio_object_key",
        existing_type=sa.VARCHAR(length=512),
        comment="旁白 wav 的 MinIO 对象路径",
        existing_comment="旁白 wav 对象路径",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_regions",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="区域级高亮配置 {regions[],sentences[]}；空=按讲稿自动判定",
        existing_comment="区域级高亮配置 {regions,sentences}；空=按讲稿自动判定",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_color",
        existing_type=sa.VARCHAR(length=16),
        comment="覆盖本页高亮主色 #RRGGBB；空=用模块设置",
        existing_comment="覆盖本页高亮主色 #RRGGBB；空=用项目设置",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "highlight_style",
        existing_type=sa.VARCHAR(length=16),
        comment="覆盖本页视觉引导样式；空=用模块设置",
        existing_comment="覆盖本页视觉引导样式；空=用项目设置",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "script_segments",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text",
        existing_comment="段级讲稿 [{text,targets[]}]：拼起来必须等于 script_text，否则视为已手改、按字面兜底",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_slide",
        "slide_no",
        existing_type=sa.INTEGER(),
        comment="页码，从 1 开始",
        existing_comment="展示页码，从 1 开始，换源后会重排",
        existing_nullable=False,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_segment",
        "duration_ms",
        existing_type=sa.INTEGER(),
        comment="片段时长(ms)",
        existing_comment="片段时长",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=_SCHEMA,
    )
    op.drop_constraint(_FK_CREATED, "ppt_video_script_revision", schema=_SCHEMA, type_="foreignkey")
    op.drop_constraint(_FK_UPDATED, "ppt_video_script_revision", schema=_SCHEMA, type_="foreignkey")
    op.alter_column(
        "ppt_video_script_revision",
        "applied",
        existing_type=sa.BOOLEAN(),
        comment="是否仍生效",
        existing_comment="是否仍生效；回滚后置 false",
        existing_nullable=False,
        existing_server_default=sa.text("true"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "after",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="改写后讲稿快照 {slide_uid: text}",
        existing_comment="改写后快照 {slide_uid: text}",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_script_revision",
        "before",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        comment="改写前讲稿快照 {slide_uid: text}",
        existing_comment="改写前快照 {slide_uid: text}",
        existing_nullable=True,
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_project",
        "slide_count",
        existing_type=sa.INTEGER(),
        comment="幻灯片页数",
        existing_comment="页数",
        existing_nullable=False,
        existing_server_default=sa.text("0"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_job",
        "max_attempts",
        existing_type=sa.INTEGER(),
        comment="最大尝试次数",
        existing_comment="重试上限",
        existing_nullable=False,
        existing_server_default=sa.text("3"),
        schema=_SCHEMA,
    )
    op.alter_column(
        "ppt_video_job",
        "stage",
        existing_type=sa.VARCHAR(length=32),
        comment="阶段: queued/parse/render/tts/concat/upload",
        existing_comment="queued/parse/render/tts/concat/upload",
        existing_nullable=False,
        existing_server_default=sa.text("'queued'::character varying"),
        schema=_SCHEMA,
    )
