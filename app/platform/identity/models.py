import uuid

from sqlalchemy import (
    JSON,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class User(BaseModel):
    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint("employee_no", name="uq_identity_users_employee_no"),
        UniqueConstraint("feishu_user_id", name="uq_identity_users_feishu_user_id"),
        {"schema": "identity"},
    )

    name: Mapped[str] = mapped_column(String(100))
    employee_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    department: Mapped[str | None] = mapped_column(String(200), nullable=True)
    position: Mapped[str | None] = mapped_column(String(200), nullable=True)
    mobile: Mapped[str | None] = mapped_column(String(32), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    feishu_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    feishu_open_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    feishu_union_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    en_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="英文名"
    )
    avatar_thumb: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="小头像URL"
    )
    avatar_middle: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="中头像URL"
    )
    avatar_big: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="大头像URL"
    )
    enterprise_email: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="企业邮箱"
    )
    tenant_key: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="租户标识"
    )
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    feishu_department_ids: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="飞书部门ID列表，JSON数组"
    )
    external_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    role: Mapped[str] = mapped_column(
        String(50), default="member", comment="角色: admin/manager/member/viewer"
    )


class Department(BaseModel):
    """飞书组织架构部门（本地同步副本）"""

    __tablename__ = "departments"
    __table_args__ = (
        UniqueConstraint(
            "feishu_department_id",
            name="uq_identity_departments_feishu_id",
        ),
        {"schema": "identity"},
    )

    feishu_department_id: Mapped[str] = mapped_column(
        String(64), unique=True, comment="飞书部门 open_department_id"
    )
    name: Mapped[str] = mapped_column(String(200), comment="部门名称")
    parent_feishu_department_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="父部门 ID"
    )
    leader_user_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="部门主管 user_id"
    )
    member_count: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="部门成员数"
    )
    status_is_deleted: Mapped[bool | None] = mapped_column(
        comment="飞书侧是否已删除", nullable=True, default=False
    )
    path: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="部门路径 JSON，如 [{'name':'公司','id':'xxx'},...]",
    )
    order: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="同级排序"
    )


class LoginLog(BaseModel):
    """登录记录"""

    __tablename__ = "login_logs"
    __table_args__ = (
        Index("idx_login_logs_user_id", "user_id"),
        Index("idx_login_logs_created_at", "created_at"),
        Index("idx_login_logs_status", "status"),
        {"schema": "identity"},
    )

    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("identity.users.id"),
        nullable=True,
        comment="登录用户ID，失败时可能为None",
    )
    user_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="用户姓名（冗余，便于查询）"
    )
    login_type: Mapped[str] = mapped_column(
        String(32), default="feishu_sso", comment="登录方式：feishu_sso"
    )
    status: Mapped[str] = mapped_column(
        String(20), comment="登录结果：success / failed"
    )
    ip_address: Mapped[str | None] = mapped_column(
        String(64), nullable=True, comment="登录IP"
    )
    user_agent: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="浏览器UA"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="失败原因"
    )
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True, comment="额外信息")
