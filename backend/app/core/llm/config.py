"""LLM configuration management."""

import json
import logging
import os
import uuid
from dataclasses import dataclass, field

from sqlalchemy import JSON, Boolean, Float, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import async_session_factory
from app.shared.base_model import BaseModel

from .encryption import decrypt_api_key
from .exceptions import LLMConfigError

logger = logging.getLogger(__name__)

__all__ = [
    "LLMConfigData",
    "LLMConfigModel",
    "get_active_config",
    "get_config",
    "get_config_by_id",
    "get_env_config",
    "list_visible_configs",
]


def parse_available_models(raw: object, default_model: str) -> list[str]:
    """把库里的模型清单解析成去重保序的字符串列表。

    兼容三种历史/异常形态：NULL、JSON 数组、逗号分隔字符串。
    `model_name` 是默认模型，必须出现在清单里（旧数据只有它是常态）。
    """
    items: list[str] = []
    if isinstance(raw, list):
        items = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str) and raw.strip():
        try:
            parsed = json.loads(raw)
        except ValueError:
            parsed = None
        if isinstance(parsed, list):
            items = [str(item).strip() for item in parsed if str(item).strip()]
        else:
            items = [part.strip() for part in raw.split(",") if part.strip()]

    seen: set[str] = set()
    models: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            models.append(item)

    default = (default_model or "").strip()
    if default and default not in seen:
        models.insert(0, default)
    return models


@dataclass
class LLMConfigData:
    """LLM configuration data."""

    id: str
    config_name: str
    config_type: str  # "text" or "vision"
    api_base_url: str
    api_key: str  # Decrypted API key
    model_name: str
    temperature: float
    timeout_seconds: int
    is_active: bool
    # system=平台预置（所有人可选）；personal=个人私有（仅 owner 可见可用）
    visibility: str = "system"
    owner_user_id: str | None = None
    #: 该配置可选的模型清单；`model_name` 恒为默认模型（清单内）
    available_models: list[str] = field(default_factory=list)


class LLMConfigModel(BaseModel):
    """Database model for LLM configuration."""

    __tablename__ = "llm_configs"
    __table_args__ = {"schema": "core", "comment": "LLM configuration table"}

    config_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Configuration name")
    config_type: Mapped[str] = mapped_column(
        String(20),
        default="text",
        server_default="text",
        nullable=False,
        comment="Config type: text (text model) / vision (vision model)",
    )
    api_base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="API base URL")
    encrypted_api_key: Mapped[str] = mapped_column(String(1000), nullable=False, comment="Encrypted API key")
    model_name: Mapped[str] = mapped_column(String(128), nullable=False, comment="Model name")
    available_models: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="该配置可选的模型清单；空=只有 model_name（兼容一配置一模型）",
    )
    temperature: Mapped[float] = mapped_column(
        Float, default=0.1, server_default="0.1", nullable=False, comment="Temperature"
    )
    timeout_seconds: Mapped[int] = mapped_column(
        Integer,
        default=120,
        server_default="120",
        nullable=False,
        comment="Timeout seconds",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
        comment="Is active config",
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True, comment="Notes")
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, comment="个人配置归属用户；系统配置为空"
    )
    visibility: Mapped[str] = mapped_column(
        String(16),
        default="system",
        server_default="system",
        nullable=False,
        comment="system=平台预置所有人可选；personal=仅 owner 可见可用",
    )

    def to_config_data(self) -> LLMConfigData:
        """Convert to config data with decrypted API key."""
        return LLMConfigData(
            id=str(self.id),
            config_name=self.config_name,
            config_type=self.config_type,
            api_base_url=self.api_base_url,
            api_key=decrypt_api_key(self.encrypted_api_key),
            model_name=self.model_name,
            temperature=self.temperature,
            timeout_seconds=self.timeout_seconds,
            is_active=self.is_active,
            visibility=self.visibility,
            owner_user_id=str(self.owner_user_id) if self.owner_user_id else None,
            available_models=parse_available_models(self.available_models, self.model_name),
        )

    @property
    def is_personal(self) -> bool:
        return self.visibility == "personal"


async def get_active_config(config_type: str = "text") -> LLMConfigData | None:
    """Get active LLM config from database.

    Args:
        config_type: "text" or "vision"

    Returns:
        LLMConfigData or None if not found
    """
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(LLMConfigModel).where(
                    LLMConfigModel.is_active,
                    LLMConfigModel.config_type == config_type,
                    LLMConfigModel.visibility == "system",
                    ~LLMConfigModel.is_deleted,
                )
            )
            config = result.scalar_one_or_none()
            if config:
                return config.to_config_data()
    except Exception:
        # Database table doesn't exist or other error, fall back to env
        logger.warning("忽略异常 @ %s", "get_active_config", exc_info=True)
    return None


async def get_config_by_id(
    config_id: str,
    config_type: str = "text",
    owner_user_id: str | None = None,
) -> LLMConfigData | None:
    """按 id 取一条可用配置。

    个人私有配置只有 owner 本人能用；系统配置对所有调用方可见。
    找不到、类型不符、已删除、越权访问统一返回 None，由调用方决定降级策略。
    """
    try:
        async with async_session_factory() as session:
            result = await session.execute(
                select(LLMConfigModel).where(
                    LLMConfigModel.id == config_id,
                    LLMConfigModel.config_type == config_type,
                    ~LLMConfigModel.is_deleted,
                )
            )
            config = result.scalar_one_or_none()
            if not config:
                return None
            if config.visibility == "personal" and str(config.owner_user_id) != str(owner_user_id or ""):
                return None
            return config.to_config_data()
    except Exception:
        logger.warning("忽略异常 @ %s", "get_config_by_id", exc_info=True)
        return None


async def list_visible_configs(config_type: str = "text", owner_user_id: str | None = None) -> list[LLMConfigData]:
    """列出该用户可选的全部配置：系统预置 + 本人私有。"""
    try:
        async with async_session_factory() as session:
            stmt = select(LLMConfigModel).where(
                LLMConfigModel.config_type == config_type,
                ~LLMConfigModel.is_deleted,
                (LLMConfigModel.visibility == "system")
                | ((LLMConfigModel.visibility == "personal") & (LLMConfigModel.owner_user_id == owner_user_id)),
            )
            result = await session.execute(stmt.order_by(LLMConfigModel.visibility, LLMConfigModel.created_at))
            return [row.to_config_data() for row in result.scalars().all()]
    except Exception:
        logger.warning("忽略异常 @ %s", "list_visible_configs", exc_info=True)
        return []


def get_env_config() -> LLMConfigData | None:
    """Get LLM config from environment variables (for local dev).

    Returns:
        LLMConfigData or None if not configured
    """
    api_key = os.getenv("LLM_API_KEY")
    base_url = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
    model = os.getenv("LLM_MODEL", "deepseek-chat")

    if not api_key:
        return None

    return LLMConfigData(
        id="env",
        config_name="Environment Config",
        config_type="text",
        api_base_url=base_url,
        api_key=api_key,
        model_name=model,
        temperature=0.1,
        timeout_seconds=120,
        is_active=True,
        available_models=[model],
    )


async def get_config(config_type: str = "text") -> LLMConfigData:
    """Get LLM config - tries DB first, falls back to env.

    Args:
        config_type: "text" or "vision"

    Returns:
        LLMConfigData

    Raises:
        LLMConfigError: If no config is available
    """
    # Try DB config first (production/staging)
    config = await get_active_config(config_type)
    if config:
        return config

    # Fall back to env config (local dev)
    config = get_env_config()
    if config:
        return config

    raise LLMConfigError("LLM not configured. Set LLM_API_KEY in .env or configure via admin UI.")
