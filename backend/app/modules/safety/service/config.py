"""Safety AI 模型工厂."""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.repository import SafetyRepository

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# AI 模型配置（从环境变量读取，支持部署时覆盖）
# ═══════════════════════════════════════════════════════════


async def create_ai_service(config_type: str = "text") -> Any:
    """创建 AI 服务实例（使用全局 llm_client 单例）。

    config_type: "text"（文本模型）或 "vision"（视觉模型）

    返回 llm_client 单例，配置从 core.llm_configs 表读取。
    """
    from app.platform.integrations.ai import get_ai_service

    logger.debug("使用全局 llm_client 适配器 (config_type=%s)", config_type)
    return get_ai_service()


class ConfigService:
    """AI workflow config CRUD service."""

    def __init__(self, session: AsyncSession):
        self.repo = SafetyRepository(session)
        self.session = session

    async def get_ai_workflow_configs(
        self,
        skip: int = 0,
        limit: int = 100,
        module_code: str | None = None,
        is_enabled: bool | None = None,
    ) -> tuple[list[Any], int]:
        return await self.repo.get_ai_workflow_configs(skip, limit, module_code, is_enabled)  # type: ignore[attr-defined,no-any-return]

    async def get_ai_workflow_config(self, config_id: uuid.UUID) -> Any:
        return await self.repo.get_ai_workflow_config_by_id(config_id)  # type: ignore[attr-defined]

    async def create_ai_workflow_config(self, data: Any) -> Any:
        task_data = data.model_dump() if hasattr(data, "model_dump") else data
        return await self.repo.create_ai_workflow_config(task_data)  # type: ignore[attr-defined]

    async def update_ai_workflow_config(self, config_id: uuid.UUID, data: Any) -> Any:
        update_data = data.model_dump(exclude_unset=True) if hasattr(data, "model_dump") else data
        return await self.repo.update_ai_workflow_config(config_id, update_data)  # type: ignore[attr-defined]

    async def delete_ai_workflow_config(self, config_id: uuid.UUID) -> bool:
        return await self.repo.delete_ai_workflow_config(config_id)  # type: ignore[attr-defined,no-any-return]
