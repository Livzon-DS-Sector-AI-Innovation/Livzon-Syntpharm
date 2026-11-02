"""AI/LLM integration adapter for OpenAI-compatible APIs."""

from functools import lru_cache

from app.platform.integrations.ai.client import AIOutputError, AIService

__all__ = ["AIService", "AIOutputError", "get_ai_service"]


@lru_cache
def get_ai_service() -> AIService:
    """Factory: 返回统一走全局 llm_client 的适配器（配置来自 core.llm_configs）。"""
    return AIService()
