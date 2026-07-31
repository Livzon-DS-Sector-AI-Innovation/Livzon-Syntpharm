"""Safety AI 模型工厂."""

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.safety.repository import SafetyRepository
from app.shared.config_reader import get_module_setting

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# AI 模型配置（从环境变量读取，支持部署时覆盖）
# ═══════════════════════════════════════════════════════════


async def _get_ai_config() -> dict[str, Any]:
    """读取 AI 模型配置，从数据库读取，不提供硬编码默认值。"""
    _text_key = await get_module_setting("safety", "SAFETY_AI_TEXT_API_KEY", "")
    _vision_key = await get_module_setting("safety", "SAFETY_AI_VISION_API_KEY", "")
    if not _text_key:
        raise RuntimeError("配置 SAFETY_AI_TEXT_API_KEY 未配置，无法初始化 AI 文本模型。请在管理界面中配置该参数。")
    if not _vision_key:
        raise RuntimeError("配置 SAFETY_AI_VISION_API_KEY 未配置，无法初始化 AI 视觉模型。请在管理界面中配置该参数。")
    return {
        "text": {
            "api_key": _text_key,
            "base_url": await get_module_setting("safety", "SAFETY_AI_TEXT_BASE_URL", "https://api.deepseek.com"),
            "model": await get_module_setting("safety", "SAFETY_AI_TEXT_MODEL", "deepseek-v4-flash"),
            "temperature": 0.1,
            "timeout": 120,
        },
        "vision": {
            "api_key": _vision_key,
            "base_url": await get_module_setting(
                "safety",
                "SAFETY_AI_VISION_BASE_URL",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
            "model": await get_module_setting("safety", "SAFETY_AI_VISION_MODEL", "qwen-vl-max"),
            "temperature": 0.1,
            "timeout": 120,
        },
    }


async def create_ai_service(config_type: str = "text") -> Any:
    """创建 AI 服务实例（从数据库读取配置）。

    config_type: "text"（文本模型）或 "vision"（视觉模型）
    """
    from app.platform.integrations.ai.client import AIService

    cfg = (await _get_ai_config()).get(config_type)
    if not cfg:
        raise ValueError(f"不支持的 AI 配置类型: {config_type}，可选: text / vision")

    logger.debug("创建 AI 服务: config_type=%s model=%s", config_type, cfg["model"])
    return AIService(
        api_key=cfg["api_key"],
        base_url=cfg["base_url"],
        model=cfg["model"],
        timeout=cfg["timeout"],
    )


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
