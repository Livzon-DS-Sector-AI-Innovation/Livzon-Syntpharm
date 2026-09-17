"""文档生成 ORM 模型（schema=research）。"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel

JOB_STATUS_VALUES = (
    "draft",  # 草稿：报告与任务已建，资料/补充信息仍可改，未点「AI 提取信息」
    "pending",
    "parsing",
    "extracting",
    "awaiting_review",  # 提取完成：提取信息可编辑
    "confirmed",
    "composing",  # AI 报告生成中：成文模型按已验证取值写正文
    "rendering",
    "completed",  # 完成：产物已生成可下载
    "ready",  # 旧版完成态（兼容存量任务读取）
    "failed",
    "cancelled",
)

# 提取阶段：期间报告与任务的全部输入锁定不可编辑
EXTRACTING_STATUSES = ("pending", "parsing", "extracting")
# 生成阶段：点「AI 报告生成」之后、出稿之前
GENERATING_STATUSES = ("confirmed", "composing", "rendering")
# 允许改输入（上传/删除资料、重新提取）的状态
EDITABLE_INPUT_STATUSES = ("draft", "awaiting_review", "failed")
# 占用 worker 的执行中状态
RUNNING_STATUSES = ("parsing", "extracting", "composing", "rendering", "confirmed")


class DocGenJob(BaseModel):
    """一次「资料 → 模板 → 初版文档」的生成任务。"""

    __tablename__ = "doc_gen_jobs"
    __table_args__ = (
        Index("ix_research_doc_gen_jobs_status_created", "status", "created_at"),
        {"schema": "research"},
    )

    report_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.rd_reports.id"), nullable=True, comment="关联研发报告"
    )
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.rd_projects.id"), nullable=True, comment="关联研发项目"
    )
    # 「重新生成」不原地重跑：新建一次任务并指回上一次，旧产物与审计链完整保留
    parent_job_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("research.doc_gen_jobs.id"),
        nullable=True,
        comment="上一次生成任务（重新生成溯源）",
    )
    # 人工补充说明：以 role=supplement 的虚拟资料块参与提取与成文，
    # 「重新生成」复制到新任务后即成为使用者的长期背景知识
    supplement_text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="人工补充说明文本")
    template_code: Mapped[str] = mapped_column(String(100), comment="模板编码")
    template_version: Mapped[str] = mapped_column(String(20), comment="模板版本")
    # 生成所用母本的版本：既用于产物追溯「这一稿是哪版母本渲染的」，
    # 也用于反查「某版母本被哪些任务用过」。
    deliverable_template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("research.rd_deliverable_template_versions.id"),
        nullable=True,
        comment="所用交付物模板版本",
    )
    status: Mapped[str] = mapped_column(String(32), default="pending", comment="任务状态")
    step: Mapped[str] = mapped_column(String(64), default="排队中", comment="当前步骤说明")
    progress: Mapped[int] = mapped_column(Integer, default=0, comment="进度百分比")
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="受控编码/版本号/品种名等元数据")
    docx_object_key: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="产物 docx 存储键")
    report_object_key: Mapped[str | None] = mapped_column(String(500), nullable=True, comment="生成说明存储键")
    stats: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="渲染统计")
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True, comment="错误码")
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True, comment="错误说明")
    attempts: Mapped[int] = mapped_column(Integer, default=0, comment="已尝试次数")
    lease_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="租约到期"
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="完成时间")


class DocGenInputFile(BaseModel):
    """任务上传的资料文件。"""

    __tablename__ = "doc_gen_input_files"
    __table_args__ = ({"schema": "research"},)

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.doc_gen_jobs.id"), comment="所属任务"
    )
    original_filename: Mapped[str] = mapped_column(String(500), comment="原始文件名")
    object_key: Mapped[str] = mapped_column(String(500), comment="存储键或本地路径")
    file_id: Mapped[str] = mapped_column(String(64), comment="解析与引用用的稳定标识")
    sha256: Mapped[str] = mapped_column(String(64), comment="内容哈希")
    size_bytes: Mapped[int] = mapped_column(BigInteger, default=0, comment="字节数")
    mime_type: Mapped[str | None] = mapped_column(String(200), nullable=True, comment="MIME")
    role: Mapped[str] = mapped_column(String(32), default="material", comment="material/literature")
    page_count: Mapped[int] = mapped_column(Integer, default=0, comment="页数/行数估计")
    char_count: Mapped[int] = mapped_column(Integer, default=0, comment="解析字符数")
    parse_status: Mapped[str] = mapped_column(
        String(32), default="pending", comment="pending/done/failed/skipped/ai_fallback"
    )
    warnings: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, comment="解析告警")


class DocGenSlotValue(BaseModel):
    """任务级槽位结果（用于排查与统计，不作为在线编辑入口）。"""

    __tablename__ = "doc_gen_slot_values"
    __table_args__ = ({"schema": "research"},)

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.doc_gen_jobs.id"), comment="所属任务"
    )
    # 动态章节的槽位 key 形如 ``route_study__0.yield``，比骨架槽位长得多，故放宽到 200
    slot_key: Mapped[str] = mapped_column(String(200), comment="槽位 key（章节槽位带实例前缀）")
    section_key: Mapped[str | None] = mapped_column(
        String(150), nullable=True, comment="所属章节实例 key；骨架槽位为空"
    )
    instance_index: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="章节实例序号")
    label: Mapped[str] = mapped_column(String(200), comment="槽位名称")
    text: Mapped[str | None] = mapped_column(Text, nullable=True, comment="渲染文本")
    # 成文（AI 报告生成）会改写 text，人工确认值另存这里，便于回退与对照
    pre_compose_text: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="成文前的人工确认文本（未成文时为空）"
    )
    rows: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, comment="表格行数据")
    state: Mapped[str] = mapped_column(String(32), comment="结果状态")
    reason: Mapped[str | None] = mapped_column(Text, nullable=True, comment="原因说明")
    confidence: Mapped[float | None] = mapped_column(nullable=True, comment="模型置信度")
    evidence: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, comment="依据（文件/页码/原文）")
    candidates: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, comment="冲突候选值")


class DocGenConversation(BaseModel):
    """任务对话会话：初抽完成后自动创建，一个任务一个会话。

    对话阶段只做「补值」——把用户口述的信息写进 doc_gen_slot_values，
    渲染仍走既有 confirm 链路，会话本身不改变任务状态机。
    """

    __tablename__ = "doc_gen_conversations"
    __table_args__ = (
        UniqueConstraint("job_id", name="uq_research_doc_gen_conversations_job_id"),
        {"schema": "research"},
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.doc_gen_jobs.id"), comment="所属任务"
    )
    status: Mapped[str] = mapped_column(String(16), default="active", comment="active/completed/skipped")
    round_count: Mapped[int] = mapped_column(Integer, default=0, comment="已完成对话轮数")
    max_rounds: Mapped[int] = mapped_column(Integer, default=3, comment="轮数上限（超过提示转人工确认）")
    snapshot: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="创建时的槽位盘点快照")


class DocGenMessage(BaseModel):
    """会话消息：用户回复、助手追问（含盘点卡）与每次带来的槽位变更。"""

    __tablename__ = "doc_gen_messages"
    __table_args__ = (
        Index("ix_research_doc_gen_messages_conv_created", "conversation_id", "created_at"),
        {"schema": "research"},
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.doc_gen_conversations.id"), comment="所属会话"
    )
    role: Mapped[str] = mapped_column(String(16), comment="user/assistant")
    content: Mapped[str] = mapped_column(Text, comment="消息内容（盘点卡为 Markdown 文本）")
    slot_updates: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, comment="本条消息写入的槽位变更")


class DocGenSection(BaseModel):
    """任务的大纲：一个动态章节实例。

    结构决策（触发判定 + 人工调整）的结果落在这里，渲染阶段只按它插标题。
    ``trigger_trace`` 保留「为何出现 / 为何不出现」的判定依据，是结构可解释性的来源。
    """

    __tablename__ = "doc_gen_sections"
    __table_args__ = (
        Index("ix_research_doc_gen_sections_job_order", "job_id", "order_index"),
        {"schema": "research"},
    )

    job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("research.doc_gen_jobs.id"), comment="所属任务"
    )
    section_key: Mapped[str] = mapped_column(String(150), comment="章节实例 key，如 route_study__0")
    fragment_key: Mapped[str] = mapped_column(String(100), comment="来源章节片段 key")
    extension_point_key: Mapped[str] = mapped_column(String(100), comment="挂载的扩展点 key")
    parent_section_key: Mapped[str | None] = mapped_column(String(150), nullable=True, comment="父章节实例 key")
    level: Mapped[int] = mapped_column(Integer, default=1, comment="标题层级")
    title: Mapped[str] = mapped_column(String(300), comment="章节标题（不含编号）")
    order_index: Mapped[int] = mapped_column(Integer, default=0, comment="渲染顺序")
    source: Mapped[str] = mapped_column(String(16), default="auto", comment="auto/manual")
    state: Mapped[str] = mapped_column(String(16), default="enabled", comment="enabled/disabled")
    trigger_trace: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True, comment="触发判定依据")
