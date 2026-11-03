"""智能体模块 ORM models —— PPT 配音视频。

六张表都在 `agent` schema 下：

- `ppt_video_project`  ：配音视频项目（源 PPT、默认语言/音色、最近一次正文指纹）
- `ppt_video_slide`    ：逐页讲稿与语言/音色覆盖、页图与音频指纹
- `ppt_video_segment`  ：页片段缓存索引（segment_key → MinIO 对象），跨项目复用
- `ppt_video_version`  ：一次渲染产出的 MP4 + manifest（复用取证）
- `ppt_video_job`      ：渲染队列（跨进程抢占，worker 消费）
- `ppt_video_script_revision`：讲稿修订记录（改写/换源快照，回滚依据）

正文指纹 `body_key` 只覆盖第 2 页起，片头不参与，这是「只换片头不重做正文」的落点。

页身份说明：`slide_no` 是可重排的**展示序号**，`slide_uid` 才是稳定身份。
插页/删页只会改动 `slide_no`，讲稿、音频、页图 key 全部挂在 `slide_uid` 上。
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel

_SCHEMA = {"schema": "agent"}

# 项目状态
PROJECT_STATUS_DRAFT = "draft"
PROJECT_STATUS_RENDERING = "rendering"
PROJECT_STATUS_READY = "ready"
PROJECT_STATUS_FAILED = "failed"

# 任务状态
JOB_STATUS_QUEUED = "queued"
JOB_STATUS_RUNNING = "running"
JOB_STATUS_SUCCEEDED = "succeeded"
JOB_STATUS_FAILED = "failed"
JOB_STATUS_CANCELED = "canceled"

# 项目级 AI 讲稿初稿状态
SCRIPT_AI_STATUS_IDLE = "idle"
SCRIPT_AI_STATUS_QUEUED = "queued"
SCRIPT_AI_STATUS_RUNNING = "running"
SCRIPT_AI_STATUS_DONE = "done"
SCRIPT_AI_STATUS_PARTIAL = "partial"
SCRIPT_AI_STATUS_FAILED = "failed"
SCRIPT_AI_STATUS_DISABLED = "disabled"

# 单页讲稿来源
SCRIPT_SOURCE_UPLOAD = "upload"
SCRIPT_SOURCE_AI = "ai"
SCRIPT_SOURCE_MANUAL = "manual"

# 讲稿改写语义
REWRITE_MODE_FILL_BLANK = "fill_blank"
REWRITE_MODE_REWRITE_ALL = "rewrite_all"
REWRITE_MODE_REWRITE_SELECTED = "rewrite_selected"
REWRITE_MODE_REWRITE_ONE = "rewrite_one"
REWRITE_MODE_SOURCE_REPLACE = "source_replace"

REWRITE_MODES = (
    REWRITE_MODE_FILL_BLANK,
    REWRITE_MODE_REWRITE_ALL,
    REWRITE_MODE_REWRITE_SELECTED,
    REWRITE_MODE_REWRITE_ONE,
    REWRITE_MODE_SOURCE_REPLACE,
)

# 修订记录状态（复用任务状态语义，独立常量避免跨表耦合）
REVISION_STATUS_QUEUED = "queued"
REVISION_STATUS_RUNNING = "running"
REVISION_STATUS_SUCCEEDED = "succeeded"
REVISION_STATUS_FAILED = "failed"


class PptVideoProject(BaseModel):
    """一个配音视频项目。"""

    __tablename__ = "ppt_video_project"
    __table_args__ = (
        Index("ix_agent_ppt_video_project_status", "status", postgresql_where=text("is_deleted = false")),
        Index("ix_agent_ppt_video_project_body_key", "body_key"),
        _SCHEMA,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="项目名（也是视频文件名前缀）")
    source_filename: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始 PPT 文件名")
    source_object_key: Mapped[str] = mapped_column(String(512), nullable=False, comment="源 PPT 的 MinIO 对象路径")
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False, comment="源 PPT 文件指纹")
    slide_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="页数")
    default_language: Mapped[str] = mapped_column(
        String(8), default="zh", server_default="zh", nullable=False, comment="默认旁白语言: zh/en"
    )
    default_voice_id: Mapped[str] = mapped_column(
        String(32), default="zf_001", server_default="zf_001", nullable=False, comment="默认音色 ID"
    )
    speed: Mapped[float] = mapped_column(
        Float, default=1.0, server_default="1.0", nullable=False, comment="默认语速 0.5~2.0"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        default=PROJECT_STATUS_DRAFT,
        server_default=PROJECT_STATUS_DRAFT,
        nullable=False,
        comment="draft/rendering/ready/failed",
    )
    head_key: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="最近一次渲染的片头片段指纹")
    body_key: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="最近一次渲染的正文块指纹")
    body_input_key: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="最近一次渲染的正文输入签名（判断正文是否已变更）"
    )
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="最近一次失败原因")
    script_ai_status: Mapped[str] = mapped_column(
        String(16),
        default=SCRIPT_AI_STATUS_IDLE,
        server_default=SCRIPT_AI_STATUS_IDLE,
        nullable=False,
        comment="AI 讲稿初稿状态: idle/queued/running/done/partial/failed/disabled",
    )
    script_ai_error: Mapped[str | None] = mapped_column(Text, nullable=True, comment="AI 讲稿初稿最近一次失败原因")
    script_ai_progress: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, comment="AI 讲稿初稿进度 0~100"
    )
    llm_config_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="项目级模型覆盖（core.llm_configs.id）；空=跟随全局默认"
    )
    script_guide: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="项目级讲稿风格指南；空=继承全局"
    )
    source_version: Mapped[int] = mapped_column(
        Integer, default=1, server_default="1", nullable=False, comment="源 PPT 版本号，对象 key 为 source-v{n}.pptx"
    )

    def body_is_stale(self, current_body_key: str) -> bool:
        """已渲染过、且当前正文指纹与上次渲染不一致 → 提示「需重新生成」。"""
        return bool(self.body_key) and self.body_key != current_body_key


class PptVideoSlide(BaseModel):
    """一页幻灯片：讲稿 + 语言/音色覆盖 + 页图与音频指纹。"""

    __tablename__ = "ppt_video_slide"
    __table_args__ = (
        # 页码在换源重排时会整体平移，唯一约束必须可延迟，否则同一事务内必然中途撞车
        UniqueConstraint(
            "project_id",
            "slide_no",
            name="uq_agent_ppt_video_slide_project_no",
            deferrable=True,
            initially="DEFERRED",
        ),
        UniqueConstraint("project_id", "slide_uid", name="uq_agent_ppt_video_slide_project_uid"),
        _SCHEMA,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent.ppt_video_project.id"), nullable=False, comment="所属项目"
    )
    slide_uid: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        default=uuid.uuid4,
        nullable=False,
        comment="稳定身份：换源对齐、讲稿/音频/页图归属都挂在它上面",
    )
    slide_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="展示页码，从 1 开始，换源后会重排")
    source_index: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False, comment="当前源 PPT 中的页序（1 起）"
    )
    script_text: Mapped[str] = mapped_column(Text, default="", server_default="", nullable=False, comment="本页讲稿")
    language: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="覆盖语言: zh/en；空=用项目默认")
    voice_id: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="覆盖音色；空=用项目默认")
    speed: Mapped[float | None] = mapped_column(Float, nullable=True, comment="覆盖语速；空=用项目默认")
    page_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="从 PPT 解析出的本页文本（辅助填稿）")
    page_notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="PPT 演讲者备注（辅助填稿）")
    script_source: Mapped[str] = mapped_column(
        String(16),
        default="",
        server_default="",
        nullable=False,
        comment="讲稿来源: upload/ai/manual；空=无讲稿",
    )
    image_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="页图 MinIO 对象路径")
    image_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="页图指纹")
    audio_object_key: Mapped[str | None] = mapped_column(String(512), nullable=True, comment="旁白 wav 对象路径")
    audio_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="旁白 wav 指纹")
    audio_key: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="旁白内容寻址 key")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="旁白时长")
    page_fingerprint: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="页内容指纹（文字+备注+形状数+坐标摘要），用于换源对齐"
    )
    layout: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSON, nullable=True, comment="形状坐标清单：name/kind/text/left/top/width/height（EMU）"
    )
    script_stale: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False, comment="画面已变、讲稿尚未按新画面重写"
    )


class PptVideoSegment(BaseModel):
    """页片段缓存索引：同一 segment_key 只渲染一次，可跨项目复用。"""

    __tablename__ = "ppt_video_segment"
    __table_args__ = (
        UniqueConstraint("segment_key", name="uq_agent_ppt_video_segment_key"),
        _SCHEMA,
    )

    segment_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="页片段内容寻址 key")
    image_sha256: Mapped[str] = mapped_column(String(64), nullable=False, comment="页图指纹")
    audio_sha256: Mapped[str] = mapped_column(String(64), nullable=False, comment="旁白指纹")
    encoder_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="编码参数指纹")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="片段时长")
    object_key: Mapped[str] = mapped_column(String(512), nullable=False, comment="片段 MinIO 对象路径")
    file_size: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="片段字节数")


class PptVideoVersion(BaseModel):
    """一次渲染产出的成片版本。"""

    __tablename__ = "ppt_video_version"
    __table_args__ = (
        UniqueConstraint("project_id", "version_no", name="uq_agent_ppt_video_version_no"),
        _SCHEMA,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent.ppt_video_project.id"), nullable=False, comment="所属项目"
    )
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, comment="版本号，从 1 递增")
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="下载文件名（含版本标识）")
    object_key: Mapped[str] = mapped_column(String(512), nullable=False, comment="MP4 的 MinIO 对象路径")
    file_size: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="文件字节数")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="成片时长")
    file_sha256: Mapped[str] = mapped_column(String(64), nullable=False, comment="成片指纹（各版本必然不同）")
    head_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="片头片段指纹")
    body_key: Mapped[str] = mapped_column(String(64), nullable=False, comment="正文块指纹")
    manifest: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, comment="复用取证清单")


class PptVideoJob(BaseModel):
    """渲染任务队列。"""

    __tablename__ = "ppt_video_job"
    __table_args__ = (
        Index("ix_agent_ppt_video_job_pick", "status", "created_at", postgresql_where=text("is_deleted = false")),
        _SCHEMA,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent.ppt_video_project.id"), nullable=False, comment="所属项目"
    )
    status: Mapped[str] = mapped_column(
        String(16),
        default=JOB_STATUS_QUEUED,
        server_default=JOB_STATUS_QUEUED,
        nullable=False,
        comment="queued/running/succeeded/failed/canceled",
    )
    stage: Mapped[str] = mapped_column(
        String(32),
        default="queued",
        server_default="queued",
        nullable=False,
        comment="queued/parse/render/tts/concat/upload",
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="进度 0~100")
    attempts: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="已尝试次数")
    max_attempts: Mapped[int] = mapped_column(
        Integer, default=3, server_default="3", nullable=False, comment="重试上限"
    )
    worker_id: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="抢占该任务的 worker 标识")
    heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="心跳时间")
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="开始时间")
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="结束时间")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因摘要")
    requested_by_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="发起人姓名（展示用）")
    version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent.ppt_video_version.id"), nullable=True, comment="成功后产出的版本"
    )


class PptVideoScriptRevision(BaseModel):
    """一次讲稿改写 / 一次换源的可回滚快照。

    一条记录同时承担两个角色：任务记录（status/progress/error）与回滚依据（before/after）。
    回滚只是把 `before` 写回讲稿并置 `applied=false`，不删除记录，保留完整审计线索。
    """

    __tablename__ = "ppt_video_script_revision"
    __table_args__ = (
        Index(
            "ix_agent_ppt_video_script_revision_project",
            "project_id",
            "created_at",
            postgresql_where=text("is_deleted = false"),
        ),
        _SCHEMA,
    )

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agent.ppt_video_project.id"), nullable=False, comment="所属项目"
    )
    mode: Mapped[str] = mapped_column(
        String(24), nullable=False, comment="fill_blank/rewrite_all/rewrite_selected/rewrite_one/source_replace"
    )
    instruction: Mapped[str | None] = mapped_column(Text, nullable=True, comment="单次临时指令")
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True, comment="本次实际使用的模型")
    provider: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="模型来源: project/global/active/env"
    )
    scope: Mapped[list[str] | None] = mapped_column(JSON, nullable=True, comment="影响的 slide_uid 列表")
    before: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="改写前快照 {slide_uid: text}")
    after: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="改写后快照 {slide_uid: text}")
    status: Mapped[str] = mapped_column(
        String(16),
        default=REVISION_STATUS_RUNNING,
        server_default=REVISION_STATUS_RUNNING,
        nullable=False,
        comment="状态",
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False, comment="进度 0~100")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="失败原因")
    source_version: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="换源前的源文件版本号")
    applied: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False, comment="是否仍生效；回滚后置 false"
    )
    requested_by_name: Mapped[str | None] = mapped_column(String(100), nullable=True, comment="发起人姓名（展示用）")
