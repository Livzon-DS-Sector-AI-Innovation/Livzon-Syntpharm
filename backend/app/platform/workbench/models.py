"""顶栏待办已读登记。

工作台是跨模块的平台能力（把 quality / safety 的待办聚合到一起），「用户看没看过」
属于平台级 UI 状态，不归属任何业务模块；因此表放 ``core`` schema（平台基础设施），
由 ``platform/workbench`` 自己拥有，避免把 workbench 概念塞进 identity。

已读匹配规则：``(user_id, source, item_id)`` 唯一，``fingerprint`` 记录当时的内容指纹
（状态 + 当前环节 + 判定依据）。单据推进后指纹变化，旧记录不再命中 → 自动重新提醒。
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class WorkbenchTodoRead(BaseModel):
    """一条「某用户已读过某待办的某个状态」的记录。"""

    __tablename__ = "workbench_todo_reads"
    __table_args__ = (
        UniqueConstraint("user_id", "source", "item_id", name="uq_workbench_todo_reads_user_item"),
        Index("ix_workbench_todo_reads_user_id", "user_id"),
        {"schema": "core", "comment": "顶栏待办已读登记（用户 + 数据源 + 单据 + 内容指纹）"},
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("identity.users.id"),
        nullable=False,
        comment="已读用户",
    )
    source: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="数据源标识，如 quality.deviation.todos",
    )
    item_id: Mapped[str] = mapped_column(String(64), nullable=False, comment="待办条目 ID")
    fingerprint: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="内容指纹：状态|当前环节|判定依据",
    )
    read_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="最近一次标记已读时间",
    )
