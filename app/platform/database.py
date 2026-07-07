"""数据库会话管理

提供数据库会话获取功能。
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory, get_db as core_get_db

# 导出 get_db_session 作为 get_db 的别名，保持向后兼容
get_db_session = core_get_db


async def get_db() -> AsyncGenerator[AsyncSession]:
    """获取数据库会话的生成器函数"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()