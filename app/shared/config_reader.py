"""Helper functions for reading module runtime settings from database."""

import json
from typing import Any

from sqlalchemy import select

from app.core.config_model import ModuleSetting
from app.core.database import async_session_factory


async def get_module_setting(module: str, key: str, default: str = "") -> str:
    """Read a runtime setting from database.

    Falls back to default if not found.

    Args:
        module: Module name (e.g., "safety", "equipment")
        key: Setting key (e.g., "SAFETY_AI_TEXT_MODEL")
        default: Default value if not found

    Returns:
        Setting value as string
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(ModuleSetting).where(
                ModuleSetting.module == module,
                ModuleSetting.key == key,
                not ModuleSetting.is_deleted,  # type: ignore[arg-type]
            )
        )
        setting = result.scalar_one_or_none()
        if setting:
            return setting.value
    return default


async def get_module_setting_bool(module: str, key: str, default: bool = False) -> bool:
    """Read a boolean runtime setting.

    Args:
        module: Module name
        key: Setting key
        default: Default value if not found

    Returns:
        Setting value as boolean
    """
    value = await get_module_setting(module, key, str(default).lower())
    return value.lower() in ("true", "1", "yes")


async def get_module_setting_int(module: str, key: str, default: int = 0) -> int:
    """Read an integer runtime setting.

    Args:
        module: Module name
        key: Setting key
        default: Default value if not found

    Returns:
        Setting value as integer
    """
    value = await get_module_setting(module, key, str(default))
    try:
        return int(value)
    except ValueError:
        return default


async def _func_l72(module: str, key: str, default: dict[str, Any] | list[Any] | None = None) -> Any:
    """Read a JSON runtime setting.

    Args:
        module: Module name
        key: Setting key
        default: Default value if not found or invalid JSON

    Returns:
        Parsed JSON value (dict, list, etc.)
    """
    value = await get_module_setting(module, key, "")
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
