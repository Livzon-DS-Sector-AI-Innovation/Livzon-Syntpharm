"""Module runtime configuration settings — database-backed."""

import sqlalchemy as sa
from sqlalchemy import Boolean, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.shared.base_model import BaseModel


class ModuleSetting(BaseModel):
    """Runtime configuration setting for a module.

    Each setting belongs to a specific module and has a key-value pair.
    The value is stored as a string with a type hint for proper parsing.
    """

    __tablename__ = "module_settings"
    __table_args__ = (
        sa.UniqueConstraint("module", "key", name="uq_module_setting"),
        {"schema": "core", "comment": "Module runtime configuration settings"},
    )

    module: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Module name (safety, equipment, energy, hr, registration)",
    )
    key: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
        comment="Setting key (e.g., SAFETY_AI_TEXT_MODEL)",
    )
    value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Setting value (stored as string, parsed based on value_type)",
    )
    value_type: Mapped[str] = mapped_column(
        String(20),
        default="string",
        server_default="string",
        nullable=False,
        comment="Type hint: string, int, bool, json",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description for UI display",
    )
    label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="配置项中文名（未回填时界面回退显示 key）",
    )
    group_name: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="功能域分组名（未回填时归入「其他」）",
    )
    is_secret: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="是否密钥类配置（列表只返回掩码，导出不含明文）",
    )
    value_hint: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        comment="取值提示 / 取值范围（界面在编辑框中提示）",
    )
