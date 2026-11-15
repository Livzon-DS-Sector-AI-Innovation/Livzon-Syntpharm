"""Resolve AI-exam runtime settings from ``hr.system_settings``.

Deployment `.env` is no longer rewritten by the settings page, so the AI exam
job must read the same DB-backed values the UI writes. Secrets stay encrypted at
rest and are only decrypted in memory here.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.secrets import decrypt_secret

DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

_BASE_URL_KEY = "AI_BASE_URL"
_API_KEY_KEY = "AI_API_KEY"
_MODEL_KEY = "AI_MODEL"


@dataclass(frozen=True)
class AiSettings:
    base_url: str
    api_key: str
    model: str


async def load_ai_settings(session: AsyncSession) -> AiSettings:
    result = await session.execute(
        text("SELECT key, value FROM hr.system_settings WHERE key IN (:base_url, :api_key, :model)"),
        {"base_url": _BASE_URL_KEY, "api_key": _API_KEY_KEY, "model": _MODEL_KEY},
    )
    stored = {row[0]: row[1] for row in result.fetchall()}

    base_url = str(stored.get(_BASE_URL_KEY) or "").strip() or DEFAULT_BASE_URL

    raw_api_key = stored.get(_API_KEY_KEY)
    api_key = ""
    if raw_api_key:
        try:
            api_key = decrypt_secret(str(raw_api_key)).strip()
        except RuntimeError:
            raise RuntimeError("AI_API_KEY 解密失败，请在系统设置中重新保存") from None
    if not api_key:
        # Deployment fallback for environments that still provide the key in .env.
        api_key = get_settings().AI_API_KEY.strip()

    model = str(stored.get(_MODEL_KEY) or "").strip()
    if not model:
        raise ValueError("AI_MODEL 未配置，请在系统设置中填写")

    return AiSettings(base_url=base_url, api_key=api_key, model=model)
