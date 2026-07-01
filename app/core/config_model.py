"""Module runtime configuration settings — database-backed."""

import sqlalchemy as sa
from sqlalchemy import String, Text
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
        comment="Module name (safety, equipment, energy, hr, regulatory_tracker)",
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
