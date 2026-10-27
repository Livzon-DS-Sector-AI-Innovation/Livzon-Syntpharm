"""菜单栏配置读写 + 护栏校验。

存储：复用 `core.module_settings`（module=`menu`, key=`CONFIG`, value_type=json），
**不新建表、不加迁移**；未配置时返回空配置，前端按代码默认渲染（既有行为不变）。

注意：读取/写入前必须 import `app.platform.identity.models`（ModuleSetting 的
`updated_by` 外键指向 identity.users，否则报 NoReferencedTableError）。
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy import select

import app.platform.identity.models  # noqa: F401  — 注册 identity.users 供外键解析
from app.core.config_model import ModuleSetting
from app.core.database import async_session_factory
from app.core.exceptions import BadRequestException
from app.shared.module_registry import BUSINESS_MODULES

logger = logging.getLogger(__name__)

MENU_MODULE = "menu"
MENU_CONFIG_KEY = "CONFIG"

# 不可隐藏的菜单项（防自锁）：系统管理入口、以及菜单管理自身
PROTECTED_MENU_KEYS = frozenset({"settings", "settings-overview", "settings-menus"})

_PERM_SEGMENTS = 3


def _empty_config() -> dict[str, Any]:
    return {"items": {}, "custom": []}


async def load_menu_config() -> dict[str, Any]:
    """读取菜单配置（无配置/解析失败时返回空配置）。"""
    async with async_session_factory() as session:
        row = (
            await session.execute(
                select(ModuleSetting).where(
                    ModuleSetting.module == MENU_MODULE,
                    ModuleSetting.key == MENU_CONFIG_KEY,
                    ModuleSetting.is_deleted == False,  # noqa: E712
                )
            )
        ).scalar_one_or_none()

    if row is None or not row.value:
        return _empty_config()

    try:
        data = json.loads(row.value)
    except json.JSONDecodeError:
        logger.warning("菜单配置 JSON 解析失败，按空配置处理")
        return _empty_config()

    if not isinstance(data, dict):
        return _empty_config()
    return {"items": data.get("items") or {}, "custom": data.get("custom") or []}


def validate_config(items: dict[str, Any], custom: list[dict[str, Any]]) -> None:
    """护栏与格式校验（不通过直接 400，避免把菜单配坏）。"""
    # 1. 保护名单不可隐藏
    for key in PROTECTED_MENU_KEYS:
        override = items.get(key) or {}
        if override.get("visible") is False:
            raise BadRequestException(f"菜单项 {key} 不允许隐藏（系统保护）")

    # 2. 权重范围
    for key, override in items.items():
        sort = (override or {}).get("sort")
        if sort is not None and not (-9999 <= int(sort) <= 9999):
            raise BadRequestException(f"菜单项 {key} 的权重超范围（-9999 ~ 9999）")

    # 3. 权限码格式（三段式，如 platform:ops:read）；不校验是否已登记，便于预留业务权限码
    for key, override in items.items():
        for code in (override or {}).get("perms") or []:
            _validate_permission_code(code, f"菜单项 {key}")

    # 4. 自定义项
    # 合法父级有三类：① 同一批次里的其他自定义项 id；② items 里出现过的内置 key；
    # ③ 后端已知的内置模块 key（BUSINESS_MODULES）。
    # 第 ③ 类必须显式允许：前端只在「菜单项有改动」时才把它写进 items，
    # 因此往某个**没改过**的模块下挂自定义项时，该模块不会出现在 items 里
    # —— 只靠 ② 会误报「父级不存在」。
    seen_ids: set[str] = set()
    # 后端已知的内置 key：业务模块（BUSINESS_MODULES）+ 平台菜单（settings / settings-overview /
    # settings-menus，见 PROTECTED_MENU_KEYS）。菜单结构定义在前端，后端只知道这些；
    # 其余内置子菜单 key 靠前端在 items 里带上下文（见 MenuManagerClient.ensureBuiltinParents）。
    module_keys = {module.code for module in BUSINESS_MODULES} | set(PROTECTED_MENU_KEYS)
    for item in custom:
        item_id = str(item.get("id") or "")
        if not item_id:
            raise BadRequestException("自定义菜单项缺少 id")
        if item_id in seen_ids:
            raise BadRequestException(f"自定义菜单项 id 重复：{item_id}")
        seen_ids.add(item_id)

        path = str(item.get("path") or "")
        if not (path.startswith("/") or path.startswith("http://") or path.startswith("https://")):
            raise BadRequestException(f"自定义菜单项「{item.get('title') or item_id}」的路径需以 / 或 http(s):// 开头")

        sort = item.get("sort")
        if sort is not None and not (-9999 <= int(sort) <= 9999):
            raise BadRequestException(f"自定义菜单项「{item.get('title') or item_id}」的权重超范围")

        for code in item.get("perms") or []:
            _validate_permission_code(code, f"自定义菜单项「{item.get('title') or item_id}」")

        parent = item.get("parent")
        if parent and parent not in seen_ids and parent not in items and parent not in module_keys:
            # 父级允许是：同一批次的其他自定义项 id / items 里的内置 key / 内置模块 key
            raise BadRequestException(f"自定义菜单项「{item.get('title') or item_id}」的父级不存在：{parent}")


def _validate_permission_code(code: str, where: str) -> None:
    parts = str(code).split(":")
    if len(parts) != _PERM_SEGMENTS or any(not part for part in parts):
        raise BadRequestException(f"{where} 的权限码格式错误（应为 模块:资源:动作）：{code}")


async def save_menu_config(
    items: dict[str, Any],
    custom: list[dict[str, Any]],
    updated_by: uuid.UUID | None = None,
) -> dict[str, Any]:
    """保存菜单配置（幂等 upsert）。"""
    payload = {"items": items, "custom": custom}
    value = json.dumps(payload, ensure_ascii=False)

    async with async_session_factory() as session:
        # 注意：这里**不能**过滤 is_deleted —— `uq_module_setting (module, key)` 唯一约束
        # 不区分软删，若只查活跃行会走 INSERT 撞唯一约束（报「数据重复，该记录已存在」）。
        # 查到软删行时直接复活它。
        rows = list(
            (
                await session.execute(
                    select(ModuleSetting).where(
                        ModuleSetting.module == MENU_MODULE,
                        ModuleSetting.key == MENU_CONFIG_KEY,
                    )
                )
            )
            .scalars()
            .all()
        )
        row = rows[0] if rows else None

        if row is None:
            session.add(
                ModuleSetting(
                    module=MENU_MODULE,
                    key=MENU_CONFIG_KEY,
                    value=value,
                    value_type="json",
                    updated_by=updated_by,
                )
            )
        else:
            row.value = value
            row.value_type = "json"
            row.is_deleted = False
            row.updated_by = updated_by
        await session.commit()

    logger.info("菜单配置已保存（items=%d, custom=%d）", len(items), len(custom))
    return payload
