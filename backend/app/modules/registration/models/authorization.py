"""Authorization letter and supplementary reply ORM models."""

import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class AuthorizationLetter(BaseModel):
    """授权书生成记录表"""

    __tablename__ = "authorization_letters"
    __table_args__ = (
        Index("ix_authorization_letters_product_name", "product_name"),
        Index("ix_authorization_letters_registration_number", "registration_number"),
        {"schema": "registration"},
    )

    api_company: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        server_default="珠海保税区丽珠合成制药有限公司",
        comment="原料药企业名称",
    )
    product_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="产品名称（对照表标准名）")
    registration_number: Mapped[str] = mapped_column(String(32), nullable=False, comment="产品登记号")
    preparation_unit: Mapped[str] = mapped_column(
        String(256), nullable=False, comment="制剂单位名称（药品上市许可持有人/申请人）"
    )
    preparation_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="制剂名称")
    administration_route: Mapped[str] = mapped_column(String(64), nullable=False, comment="给药途径")
    template_file_key: Mapped[str] = mapped_column(String(256), nullable=False, comment="模板文件 key")
    template_file_name: Mapped[str] = mapped_column(String(256), nullable=True, comment="模板文件名")
    output_file_key: Mapped[str] = mapped_column(String(256), nullable=False, comment="生成文件 key")
    output_file_name: Mapped[str] = mapped_column(String(256), nullable=False, comment="生成文件名")
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True, comment="备注")


class ProductRegistrationNumber(BaseModel):
    """品种登记号对照表（品种名在未软删记录内唯一；入库仅新增、不覆盖）"""

    __tablename__ = "product_registration_numbers"
    __table_args__ = (
        UniqueConstraint("product_name", "is_deleted", name="uq_product_registration_numbers_name"),
        {"schema": "registration"},
    )

    product_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="品种名称")
    registration_number: Mapped[str] = mapped_column(String(32), nullable=False, comment="登记号")


class AuthorizationLetterTrail(BaseModel):
    """授权书留痕日志表（审计追踪：只增不删不改，不提供更新/删除接口）"""

    __tablename__ = "authorization_letter_trails"
    __table_args__ = (
        CheckConstraint("action IN ('generate', 'download')", name="ck_authorization_letter_trails_action"),
        Index("ix_authorization_letter_trails_letter", "letter_id"),
        {"schema": "registration"},
    )

    letter_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("registration.authorization_letters.id"),
        nullable=False,
        comment="授权书记录ID",
    )
    action: Mapped[str] = mapped_column(String(16), nullable=False, comment="动作：generate=生成 / download=下载")
    detail: Mapped[str] = mapped_column(Text, nullable=False, comment="留痕描述（生成时记模板版本）")
    # 覆盖为 Python 侧默认值：同事务内 Postgres now() 恒定，无法保证时间线倒序稳定
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(ZoneInfo("Asia/Shanghai")),
        server_default=func.now(),
    )
