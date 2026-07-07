"""AI module dependencies."""

from app.core.config import get_settings


async def get_ai_chat_service():
    from app.platform.ai.service import AiChatService

    _settings = get_settings()
    api_key = _settings.AI_API_KEY or _settings.MOONSHOT_API_KEY

    # If still no key, try reading from DB
    if not api_key:
        from app.core.database import async_session_factory
        from sqlalchemy import text as sql_text
        async with async_session_factory() as session:
            r = await session.execute(sql_text(
                "SELECT value FROM hr.system_settings WHERE key = 'AI_API_KEY'"
            ))
            row = r.fetchone()
            if row:
                api_key = row[0]

    if not api_key:
        return None

    base_url = _settings.AI_BASE_URL or "https://api.moonshot.cn/v1"
    model = _settings.AI_MODEL or "kimi-k2.5"

    # Also check DB for base_url and model
    if not _settings.AI_BASE_URL:
        from app.core.database import async_session_factory
        from sqlalchemy import text as sql_text
        async with async_session_factory() as session:
            r = await session.execute(sql_text(
                "SELECT key, value FROM hr.system_settings WHERE key IN ('AI_BASE_URL', 'AI_MODEL')"
            ))
            for row in r.fetchall():
                if row[0] == 'AI_BASE_URL' and row[1]:
                    base_url = row[1]
                elif row[0] == 'AI_MODEL' and row[1]:
                    model = row[1]

    return AiChatService(api_key=api_key, base_url=base_url, model=model)
