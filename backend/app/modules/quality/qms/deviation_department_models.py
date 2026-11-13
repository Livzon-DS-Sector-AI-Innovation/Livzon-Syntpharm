"""偏差台账依赖的组织配置 ORM 模型。

映射基线迁移里已存在的两张表，不产生 DDL：

- ``quality.department_contacts``：部门联系人（部门负责人 / 生产负责人 / 质量负责人 / QA 人员 /
  GMP 人员 / 其他联系人 / 是否生产车间），偏差审核各环节的处理人全部由此解析。
- ``quality.department_weekly_confirmations``：部门每周生产与偏差状态确认。

``qa_staff_ids`` / ``gmp_staff_ids`` / ``additional_contacts`` 存文本数组：历史上同时存在
「平台用户 UUID」与「飞书 open_id」两种写法，解析处理人时两种都要兼容。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import ARRAY, TEXT
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class DepartmentContact(BaseModel):
    """部门联系人配置。"""

    __tablename__ = "department_contacts"
    __table_args__ = (
        UniqueConstraint("department", name="department_contacts_department_key"),
        {"schema": "quality"},
    )

    department: Mapped[str] = mapped_column(String(255), nullable=False, comment="部门名称")
    dept_head_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="部门负责人",
    )
    production_head_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="生产负责人",
    )
    quality_head_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="质量负责人",
    )
    qa_reviewer_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="所属 QA",
    )
    qa_head_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="QA 负责人",
    )
    qa_staff_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(TEXT),
        nullable=True,
        comment="兼容字段：历史 QA 人员数组（[0]=所属 QA，[1]=QA 负责人），流程以 qa_reviewer_id / qa_head_id 为准",
    )
    gmp_staff_ids: Mapped[list[str] | None] = mapped_column(
        ARRAY(TEXT),
        nullable=True,
        comment="GMP 人员（周确认与未提交提醒的接收人）",
    )
    additional_contacts: Mapped[list[str] | None] = mapped_column(
        ARRAY(TEXT),
        nullable=True,
        comment="其他联系人",
    )
    is_production_workshop: Mapped[bool | None] = mapped_column(
        Boolean,
        nullable=True,
        server_default=text("false"),
        comment="是否生产车间（周确认与群体提醒按此筛选）",
    )


class DepartmentWeeklyConfirmation(BaseModel):
    """部门每周生产与偏差状态确认。"""

    __tablename__ = "department_weekly_confirmations"
    __table_args__ = (
        UniqueConstraint("department", "week_key", name="uq_dept_weekly_confirmation"),
        {"schema": "quality"},
    )

    department: Mapped[str] = mapped_column(String(255), nullable=False, comment="部门名称")
    week_key: Mapped[str] = mapped_column(String(20), nullable=False, comment="周标识，如 2026-W46")
    production_status: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="本周生产状态 production / stopped"
    )
    deviation_status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        server_default=text("'unsubmitted'"),
        comment="偏差提交情况 submitted / unsubmitted",
    )
    confirmed_by_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="确认人",
    )
    confirmed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="确认时间",
    )
