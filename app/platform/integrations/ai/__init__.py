"""AI/LLM integration adapter for OpenAI-compatible APIs."""

from functools import lru_cache

from app.platform.integrations.ai.client import AIOutputError, AIService

__all__ = ["AIService", "AIOutputError", "get_ai_service"]


@lru_cache
def get_ai_service() -> AIService:
    """Factory: build an AIService from platform settings (LLM_*)."""
    from app.core.config import get_settings

    settings = get_settings()
    return AIService(
        api_key=settings.LLM_API_KEY or "",
        base_url=settings.LLM_BASE_URL or "https://api.deepseek.com",
        model=settings.LLM_MODEL or "deepseek-chat",  # type: ignore[attr-defined]
    )
