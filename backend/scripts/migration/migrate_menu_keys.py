"""菜单 key 改名一次性迁移脚本。

前端 menu-config.ts 已将跨模块冲突的 key 增加模块前缀，旧 `core.module_settings` menu/CONFIG
中若仍保存旧 key，会导致这些配置被静默忽略、菜单回落到默认状态。

迁移策略：
- 唯一键：直接改名并删除旧 key。
- 冲突键（同名出现在多个模块）：把旧 key 的值复制到所有可能的新 key（旧配置已丢失模块上下文，复制最保守）。
- `settings`：可能是平台 settings 或 equipment-settings，脚本不自动处理，仅打印警告。
- 自定义菜单项 parent 若引用旧 key，同步更新。

Usage:
    仅预览：uv run python scripts/migration/migrate_menu_keys.py --dry-run
    执行： uv run python scripts/migration/migrate_menu_keys.py
"""

import argparse
import asyncio
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select

# 必须先导入 identity.users，否则 ModuleSetting 的 created_by FK 解析报 NoReferencedTableError
import app.platform.identity.models  # noqa: F401
from app.core.config_model import ModuleSetting
from app.core.database import async_session_factory

MENU_MODULE = "menu"
MENU_CONFIG_KEY = "CONFIG"

# old_key -> [new_keys]
_KEY_RENAME_MAP: dict[str, list[str]] = {
    # 跨模块冲突键：复制到所有候选新 key
    "inspection": ["equipment-inspection", "quality-inspection"],
    "regulation": ["safety-regulation", "registration-regulation"],
    "regulation-list": ["safety-regulation-list", "registration-regulation-list"],
    "projects": ["research-projects", "registration-projects"],
    # 唯一键
    "approval": ["administration-approval"],
}

# 高歧义键：需要人工判断，脚本不自动迁移
_AMBIGUOUS_KEYS = {"settings"}


def _migrate_items(items: dict) -> tuple[dict, list[str]]:
    """迁移 items，返回新 items 与日志。"""
    logs: list[str] = []
    new_items = dict(items)

    for old_key, new_keys in _KEY_RENAME_MAP.items():
        if old_key not in new_items:
            continue
        value = new_items.pop(old_key)
        logs.append(f"删除旧 key '{old_key}'")
        for new_key in new_keys:
            if new_key in new_items:
                logs.append(f"  新 key '{new_key}' 已存在，保留原值")
            else:
                new_items[new_key] = copy.deepcopy(value)
                logs.append(f"  新增 key '{new_key}'")

    for key in _AMBIGUOUS_KEYS & set(new_items.keys()):
        logs.append(f"警告：'{key}' 存在歧义（平台 settings / equipment-settings），未自动迁移，请人工核对")



    return new_items, logs


def _migrate_custom(custom: list[dict], new_items: dict) -> tuple[list[dict], list[str]]:
    """迁移 custom 项 parent 引用，返回新 custom 与日志。"""
    logs: list[str] = []
    new_custom: list[dict] = []

    # 建立单值反向映射（优先用第一个新 key），仅用于无歧义的 parent 引用
    single_reverse: dict[str, str] = {
        old_key: new_keys[0]
        for old_key, new_keys in _KEY_RENAME_MAP.items()
        if len(new_keys) == 1
    }

    for item in custom:
        new_item = copy.deepcopy(item)
        parent = new_item.get("parent")
        if parent and parent in single_reverse:
            new_parent = single_reverse[parent]
            new_item["parent"] = new_parent
            logs.append(f"custom 项 '{item.get('id')}' parent '{parent}' -> '{new_parent}'")
        elif parent and parent in _KEY_RENAME_MAP:
            logs.append(
                f"custom 项 '{item.get('id')}' parent '{parent}' 为歧义旧 key，未自动迁移，请人工核对"
            )
        new_custom.append(new_item)

    return new_custom, logs


async def main(dry_run: bool = False) -> None:
    async with async_session_factory() as db:
        result = await db.execute(
            select(ModuleSetting).where(
                ModuleSetting.module == MENU_MODULE,
                ModuleSetting.key == MENU_CONFIG_KEY,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            print("未发现菜单配置（menu/CONFIG），无需迁移")
            return

        try:
            data = json.loads(row.value)
        except json.JSONDecodeError as e:
            print(f"菜单配置 JSON 解析失败：{e}")
            return

        items = data.get("items") or {}
        custom = data.get("custom") or []

        new_items, item_logs = _migrate_items(items)
        new_custom, custom_logs = _migrate_custom(custom, new_items)

        if not item_logs and not custom_logs:
            print("未发现需要迁移的旧 menu key")
            return

        print("=== 预览迁移 ===")
        print(f"items 变更：{len(item_logs)} 条")
        for log in item_logs:
            print(f"  {log}")
        print(f"custom 变更：{len(custom_logs)} 条")
        for log in custom_logs:
            print(f"  {log}")

        if dry_run:
            print("\n[DRY-RUN] 未写入数据库")
            return

        data["items"] = new_items
        data["custom"] = new_custom
        row.value = json.dumps(data, ensure_ascii=False)
        await db.commit()
        print("\n完成：菜单配置已更新")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="菜单 key 改名一次性迁移")
    parser.add_argument("--dry-run", action="store_true", help="仅预览，不写入")
    args = parser.parse_args()
    asyncio.run(main(dry_run=args.dry_run))
