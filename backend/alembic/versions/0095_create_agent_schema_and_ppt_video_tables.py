"""create agent schema and ppt video tables

Revision ID: 0095_create_agent_schema_and_ppt_video_tables
Revises: 0093_quality_qms_deviation_flow_tables
Create Date: 2026-11-03

新建「智能体」顶层业务模块（code=agent）及其首个能力「PPT 配音视频」的五张表：

- ppt_video_project ：项目（源 PPT、默认语言/音色、最近一次正文指纹）
- ppt_video_slide   ：逐页讲稿与语言/音色覆盖、页图与音频指纹
- ppt_video_segment ：页片段缓存索引（跨项目复用）
- ppt_video_version ：成片版本 + manifest 取证
- ppt_video_job     ：渲染队列（worker 跨进程抢占）

建表统一用 `to_regclass` 幂等检查：历史环境可能已手工建过同名表。
仅涉及 agent schema，符合单模块迁移原则。
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "0095_create_agent_schema_and_ppt_video_tables"
down_revision: str = "0093_quality_qms_deviation_flow_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "agent"


def _table_exists(table_name: str) -> bool:
    bind = op.get_bind()
    result = bind.execute(sa.text("SELECT to_regclass(:fq_name)"), {"fq_name": f"{SCHEMA}.{table_name}"})
    return result.scalar() is not None


def _audit_columns() -> list[sa.Column]:
    """BaseModel 的审计列（created_at / updated_at / created_by / updated_by / is_deleted）。"""
    return [
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_by", UUID(as_uuid=True), nullable=True),
        sa.Column("updated_by", UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    ]


def _audit_fks(table_name: str) -> None:
    op.create_foreign_key(
        f"{table_name}_created_by_fkey",
        table_name,
        "users",
        ["created_by"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema="identity",
    )
    op.create_foreign_key(
        f"{table_name}_updated_by_fkey",
        table_name,
        "users",
        ["updated_by"],
        ["id"],
        source_schema=SCHEMA,
        referent_schema="identity",
    )


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    if not _table_exists("ppt_video_project"):
        op.create_table(
            "ppt_video_project",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False, comment="项目名（也是视频文件名前缀）"),
            sa.Column("source_filename", sa.String(255), nullable=False, comment="原始 PPT 文件名"),
            sa.Column("source_object_key", sa.String(512), nullable=False, comment="源 PPT 的 MinIO 对象路径"),
            sa.Column("source_sha256", sa.String(64), nullable=False, comment="源 PPT 文件指纹"),
            sa.Column("slide_count", sa.Integer(), nullable=False, server_default="0", comment="幻灯片页数"),
            sa.Column(
                "default_language", sa.String(8), nullable=False, server_default="zh", comment="默认旁白语言: zh/en"
            ),
            sa.Column(
                "default_voice_id", sa.String(32), nullable=False, server_default="zf_001", comment="默认音色 ID"
            ),
            sa.Column("speed", sa.Float(), nullable=False, server_default="1.0", comment="默认语速 0.5~2.0"),
            sa.Column(
                "status",
                sa.String(16),
                nullable=False,
                server_default="draft",
                comment="draft/rendering/ready/failed",
            ),
            sa.Column("head_key", sa.String(64), nullable=True, comment="最近一次渲染的片头片段指纹"),
            sa.Column("body_key", sa.String(64), nullable=True, comment="最近一次渲染的正文块指纹"),
            sa.Column(
                "body_input_key",
                sa.String(64),
                nullable=True,
                comment="最近一次渲染的正文输入签名（判断正文是否已变更）",
            ),
            sa.Column("last_error", sa.Text(), nullable=True, comment="最近一次失败原因"),
            *_audit_columns(),
            schema=SCHEMA,
        )
        _audit_fks("ppt_video_project")
        op.create_index(
            "ix_agent_ppt_video_project_status",
            "ppt_video_project",
            ["status"],
            schema=SCHEMA,
            postgresql_where=sa.text("is_deleted = false"),
        )
        op.create_index("ix_agent_ppt_video_project_body_key", "ppt_video_project", ["body_key"], schema=SCHEMA)

    if not _table_exists("ppt_video_slide"):
        op.create_table(
            "ppt_video_slide",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", UUID(as_uuid=True), nullable=False, comment="所属项目"),
            sa.Column("slide_no", sa.Integer(), nullable=False, comment="页码，从 1 开始"),
            sa.Column("script_text", sa.Text(), nullable=False, server_default="", comment="本页讲稿"),
            sa.Column("language", sa.String(8), nullable=True, comment="覆盖语言: zh/en；空=用项目默认"),
            sa.Column("voice_id", sa.String(32), nullable=True, comment="覆盖音色；空=用项目默认"),
            sa.Column("speed", sa.Float(), nullable=True, comment="覆盖语速；空=用项目默认"),
            sa.Column("page_text", sa.Text(), nullable=True, comment="从 PPT 解析出的本页文本（辅助填稿）"),
            sa.Column("page_notes", sa.Text(), nullable=True, comment="PPT 演讲者备注（辅助填稿）"),
            sa.Column("image_object_key", sa.String(512), nullable=True, comment="页图 MinIO 对象路径"),
            sa.Column("image_sha256", sa.String(64), nullable=True, comment="页图指纹"),
            sa.Column("audio_object_key", sa.String(512), nullable=True, comment="旁白 wav 的 MinIO 对象路径"),
            sa.Column("audio_sha256", sa.String(64), nullable=True, comment="旁白 wav 指纹"),
            sa.Column("audio_key", sa.String(64), nullable=True, comment="旁白内容寻址 key"),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0", comment="旁白时长(ms)"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(
                ["project_id"],
                [f"{SCHEMA}.ppt_video_project.id"],
                name="ppt_video_slide_project_id_fkey",
            ),
            sa.UniqueConstraint("project_id", "slide_no", name="uq_agent_ppt_video_slide_project_no"),
            schema=SCHEMA,
        )
        _audit_fks("ppt_video_slide")

    if not _table_exists("ppt_video_segment"):
        op.create_table(
            "ppt_video_segment",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("segment_key", sa.String(64), nullable=False, comment="页片段内容寻址 key"),
            sa.Column("image_sha256", sa.String(64), nullable=False, comment="页图指纹"),
            sa.Column("audio_sha256", sa.String(64), nullable=False, comment="旁白指纹"),
            sa.Column("encoder_key", sa.String(64), nullable=False, comment="编码参数指纹"),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0", comment="片段时长(ms)"),
            sa.Column("object_key", sa.String(512), nullable=False, comment="片段 MinIO 对象路径"),
            sa.Column("file_size", sa.Integer(), nullable=False, server_default="0", comment="片段字节数"),
            *_audit_columns(),
            sa.UniqueConstraint("segment_key", name="uq_agent_ppt_video_segment_key"),
            schema=SCHEMA,
        )
        _audit_fks("ppt_video_segment")

    if not _table_exists("ppt_video_version"):
        op.create_table(
            "ppt_video_version",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", UUID(as_uuid=True), nullable=False, comment="所属项目"),
            sa.Column("version_no", sa.Integer(), nullable=False, comment="版本号，从 1 递增"),
            sa.Column("file_name", sa.String(255), nullable=False, comment="下载文件名（含版本标识）"),
            sa.Column("object_key", sa.String(512), nullable=False, comment="MP4 的 MinIO 对象路径"),
            sa.Column("file_size", sa.Integer(), nullable=False, server_default="0", comment="文件字节数"),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0", comment="成片时长(ms)"),
            sa.Column("file_sha256", sa.String(64), nullable=False, comment="成片指纹（各版本必然不同）"),
            sa.Column("head_key", sa.String(64), nullable=False, comment="片头片段指纹"),
            sa.Column("body_key", sa.String(64), nullable=False, comment="正文块指纹"),
            sa.Column("manifest", sa.JSON(), nullable=False, comment="复用取证清单（每页 sha256 与命中情况）"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(
                ["project_id"],
                [f"{SCHEMA}.ppt_video_project.id"],
                name="ppt_video_version_project_id_fkey",
            ),
            sa.UniqueConstraint("project_id", "version_no", name="uq_agent_ppt_video_version_no"),
            schema=SCHEMA,
        )
        _audit_fks("ppt_video_version")

    if not _table_exists("ppt_video_job"):
        op.create_table(
            "ppt_video_job",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("project_id", UUID(as_uuid=True), nullable=False, comment="所属项目"),
            sa.Column(
                "status",
                sa.String(16),
                nullable=False,
                server_default="queued",
                comment="queued/running/succeeded/failed/canceled",
            ),
            sa.Column(
                "stage",
                sa.String(32),
                nullable=False,
                server_default="queued",
                comment="阶段: queued/parse/render/tts/concat/upload",
            ),
            sa.Column("progress", sa.Integer(), nullable=False, server_default="0", comment="进度 0~100"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0", comment="已尝试次数"),
            sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3", comment="最大尝试次数"),
            sa.Column("worker_id", sa.String(64), nullable=True, comment="抢占该任务的 worker 标识"),
            sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True, comment="心跳时间"),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True, comment="开始时间"),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True, comment="结束时间"),
            sa.Column("error_message", sa.Text(), nullable=True, comment="失败原因摘要"),
            sa.Column("requested_by_name", sa.String(100), nullable=True, comment="发起人姓名（展示用）"),
            sa.Column("version_id", UUID(as_uuid=True), nullable=True, comment="成功后产出的版本"),
            *_audit_columns(),
            sa.ForeignKeyConstraint(
                ["project_id"],
                [f"{SCHEMA}.ppt_video_project.id"],
                name="ppt_video_job_project_id_fkey",
            ),
            sa.ForeignKeyConstraint(
                ["version_id"],
                [f"{SCHEMA}.ppt_video_version.id"],
                name="ppt_video_job_version_id_fkey",
            ),
            schema=SCHEMA,
        )
        _audit_fks("ppt_video_job")
        op.create_index(
            "ix_agent_ppt_video_job_pick",
            "ppt_video_job",
            ["status", "created_at"],
            schema=SCHEMA,
            postgresql_where=sa.text("is_deleted = false"),
        )


def downgrade() -> None:
    for table_name in (
        "ppt_video_job",
        "ppt_video_version",
        "ppt_video_segment",
        "ppt_video_slide",
        "ppt_video_project",
    ):
        if _table_exists(table_name):
            op.drop_table(table_name, schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
