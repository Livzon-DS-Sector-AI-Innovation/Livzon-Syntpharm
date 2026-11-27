"""一次性修正库内反向书写的标准文本（如 `0.5～0.0` → `0.0～0.5`）。

只改文本字段，不动 `qc_values.level` / `numeric_value`，因此不会影响任何既有判定结果。
判定逻辑本来就用 min/max 校正，这个脚本只是把存库原文摆正，让界面看着正常。

用法（在容器内）：

    python -m app.modules.quality.qc_report.scripts.fix_standard_order
    python -m app.modules.quality.qc_report.scripts.fix_standard_order --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging

from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.quality.qc_report.models import QcItem
from app.modules.quality.qc_report.service.limits import normalize_standard_text

logger = logging.getLogger(__name__)

_LAYERS = ("legal_text", "internal_text", "sigma_text")


async def fix(dry_run: bool = False) -> int:
    """返回被修正的字段数。"""
    changed = 0
    async with async_session_factory() as session:
        items = (await session.execute(select(QcItem))).scalars().all()
        for item in items:
            for layer in _LAYERS:
                current = getattr(item, layer)
                fixed = normalize_standard_text(current)
                if fixed == current:
                    continue
                changed += 1
                logger.info(
                    "fix standard order: item=%s layer=%s %r -> %r",
                    item.item_name,
                    layer,
                    current,
                    fixed,
                )
                if not dry_run:
                    setattr(item, layer, fixed)
        if dry_run:
            await session.rollback()
        else:
            await session.commit()
    return changed


def main() -> None:
    parser = argparse.ArgumentParser(description="摆正反向书写的标准文本")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要修改的内容，不写库")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    changed = asyncio.run(fix(dry_run=args.dry_run))
    action = "待修正" if args.dry_run else "已修正"
    print(f"{action} {changed} 个标准字段")


if __name__ == "__main__":
    main()
