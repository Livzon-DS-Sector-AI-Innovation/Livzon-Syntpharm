"""按 rectification_status 回填隐患台账的关闭状态（幂等、可预览）。

背景
----
0094 把 safety.hazard_reports.status 收敛为「关闭状态」（open / closed），但此前
status 没有任何写入方，存量记录均为默认值 open，与 rectification_status='closed'
的实际业务状态不一致：台账按 status 显示「未关闭」，详情页按 rectification_status
显示「整改已关闭」。

为什么不放进 alembic
------------------
部署流水线的 migrate 服务执行 `alembic upgrade head`，正式环境同样走这条链路。
本脚本是纯数据回填、不含任何结构变更，一旦进迁移链，正式环境部署时会自动改写
生产记录。按仓库惯例（见 backfill_permission_grants_20261023.py），一次性数据
修复放 scripts/migration/，由人确认后手动执行；迁移链只保留字段变更。

用法
----
    uv run python scripts/migration/backfill_hazard_status_20261104.py           # 只预览
    uv run python scripts/migration/backfill_hazard_status_20261104.py --apply   # 实际写入
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text

from app.core.database import async_session_factory

_COUNT_SQL = text(
    "SELECT count(*) FROM safety.hazard_reports WHERE rectification_status = 'closed' AND status <> 'closed'"
)
_SAMPLE_SQL = text(
    "SELECT hazard_no, status, rectification_status FROM safety.hazard_reports "
    "WHERE rectification_status = 'closed' AND status <> 'closed' "
    "ORDER BY hazard_no LIMIT 10"
)
_BACKFILL_SQL = text(
    "UPDATE safety.hazard_reports "
    "SET status = 'closed', closed_at = COALESCE(closed_at, updated_at) "
    "WHERE rectification_status = 'closed' AND status <> 'closed'"
)


async def main(apply: bool) -> int:
    async with async_session_factory() as session:
        total = (await session.execute(_COUNT_SQL)).scalar_one()
        print(f"待回填记录: {total} 条")
        if total:
            for row in (await session.execute(_SAMPLE_SQL)).all():
                print(f"  {row.hazard_no}  status={row.status}  rectification_status={row.rectification_status}")

        if not apply:
            print("\n预览模式，未写入。确认无误后加 --apply 执行。")
            return 0
        if total == 0:
            print("无需回填。")
            return 0

        await session.execute(_BACKFILL_SQL)
        await session.commit()
        print(f"\n已回填 {total} 条。")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="按 rectification_status 回填隐患关闭状态")
    parser.add_argument("--apply", action="store_true", help="实际写入（默认只预览）")
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.apply)))
