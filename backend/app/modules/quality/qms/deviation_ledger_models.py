"""偏差台账 ORM 模型。

对应表 ``quality.deviation_ledger``，主表字段与妙搭偏差表对齐，另含调查报告（正文 + 版本）、
AI 分析、调查记录、审核意见与附件元数据（JSONB 内嵌，附件二进制存 MinIO）。
与旧表 ``quality.quality_deviations``（14 态流程模型）完全独立，互不影响。
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel

from .deviation_ledger_constants import DEVIATION_LEVELS, LEDGER_STATUSES

_STATUS_IN = ", ".join(f"'{value}'" for value in LEDGER_STATUSES)
_LEVEL_IN = ", ".join(f"'{value}'" for value in DEVIATION_LEVELS)


class DeviationLedger(BaseModel):
    """偏差台账主表。"""

    __tablename__ = "deviation_ledger"
    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_IN})", name="ck_deviation_ledger_status"),
        CheckConstraint(
            f"deviation_level IS NULL OR deviation_level IN ({_LEVEL_IN})",
            name="ck_deviation_ledger_level",
        ),
        # 系统编号唯一：编号生成走 advisory lock，这里是并发兜底
        Index("uq_deviation_ledger_code", "code", unique=True),
        # 最终编号仅在填写后唯一，软删除行不占用
        Index(
            "uq_deviation_ledger_final_code",
            "final_code",
            unique=True,
            postgresql_where=text("final_code IS NOT NULL AND is_deleted = false"),
        ),
        Index("ix_deviation_ledger_status", "status"),
        Index("ix_deviation_ledger_department", "department"),
        Index("ix_deviation_ledger_discovery_date", "discovery_date"),
        Index("ix_deviation_ledger_created_at", "created_at"),
        {"schema": "quality"},
    )

    code: Mapped[str] = mapped_column(String(32), nullable=False, comment="系统编号 PC+YYYYMMDD+3位序号")
    final_code: Mapped[str | None] = mapped_column(String(32), nullable=True, comment="最终编号（台账优先显示）")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="偏差标题")
    department: Mapped[str] = mapped_column(String(255), nullable=False, comment="所属部门（=发生部门）")
    discovery_date: Mapped[date] = mapped_column(Date, nullable=False, comment="发现日期")
    discovery_time: Mapped[str | None] = mapped_column(String(8), nullable=True, comment="发现时间 HH:MM")
    discovery_location: Mapped[str] = mapped_column(String(255), nullable=False, comment="发现地点")
    discoverer_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=False,
        comment="发现人（默认当前登录人）",
    )
    affected_items: Mapped[str] = mapped_column(Text, nullable=False, comment="受影响的产品/物料/设备/仪器")
    batch_number: Mapped[str] = mapped_column(String(255), nullable=False, comment="批号/位号/编号")
    description: Mapped[str] = mapped_column(Text, nullable=False, comment="偏差描述")
    status: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        default="pending_ai_analysis",
        server_default=text("'pending_ai_analysis'"),
        comment="状态（12 态）",
    )
    returned_step: Mapped[str | None] = mapped_column(String(40), nullable=True, comment="退回时所在环节")
    status_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="状态变更时间（超期判定基准）",
    )
    deviation_level: Mapped[str | None] = mapped_column(String(20), nullable=True, comment="分级 minor/moderate/major")
    reason_category: Mapped[str | None] = mapped_column(String(50), nullable=True, comment="原因分类")
    reporter_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=False,
        comment="上报人（创建人）",
    )
    handler_ids: Mapped[list[uuid.UUID] | None] = mapped_column(
        ARRAY(PG_UUID(as_uuid=True)),
        nullable=True,
        comment="调查人（可多人）",
    )
    needs_cross_dept_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
        comment="是否需要跨部门审核",
    )
    cross_dept_reviewers: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="跨部门审核行 [{department, investigator_ids[], review_state,"
        " approved_by, approved_name, approved_at, opinion}（review_state: pending/approved）]",
    )
    attachments: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="附件元数据 [{file_id, file_name, object_key, size, content_type, uploaded_by, uploaded_at}]",
    )
    ai_analysis: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="AI 结构化分析 {description, reason, risk_assessment, capa_suggestion}",
    )
    investigation_records: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="调查记录 [{nonconformity_description, root_cause_analysis, risk_assessment,"
        " capa_proposals[], urgent_measures, attachments[], author_id, author_name, create_time}]，旧记录为 {content}",
    )
    review_opinions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="审核意见 [{step, result, author_id, author_name, content, create_time}]",
    )
    report_content: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="调查报告正文",
    )
    report_versions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="报告版本 [{content, editor_id, editor_name, edit_time, change_summary}]",
    )


class DeviationAttachmentComment(BaseModel):
    """附件文档批注。

    与 ``review_opinions`` 严格区分：批注只描述「文档某处的问题」，不推进流程。
    关联键用 ``file_id``（上传后不变），不使用下载 URL（签名会变，批注会漂移）。
    """

    __tablename__ = "deviation_attachment_comment"
    __table_args__ = (
        CheckConstraint("status IN ('open', 'resolved')", name="ck_deviation_attachment_comment_status"),
        Index("ix_deviation_attachment_comment_file", "ledger_id", "file_id", "is_deleted"),
        Index("ix_deviation_attachment_comment_ledger", "ledger_id", "is_deleted"),
        {"schema": "quality"},
    )

    ledger_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("quality.deviation_ledger.id"),
        nullable=False,
        comment="所属偏差台账",
    )
    file_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        nullable=False,
        comment="附件 file_id（稳定关联键，非 URL）",
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="附件名快照（附件删除后仍可追溯）")
    page_no: Mapped[int | None] = mapped_column(Integer, nullable=True, comment="页码（1 起，文档级批注为空）")
    anchor_text: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="选中文本锚点（预留，Phase 2 高亮用）",
    )
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="批注正文")
    status: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default="open",
        server_default=text("'open'"),
        comment="处理状态 open / resolved",
    )
    author_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="作者姓名快照")
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True, comment="解决人")
    resolved_by_name: Mapped[str | None] = mapped_column(String(255), nullable=True, comment="解决人姓名快照")
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, comment="解决时间")
