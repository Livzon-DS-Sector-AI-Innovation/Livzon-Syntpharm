"""一次性数据修正：把日数据与预警记录的日期整体补回东八区那一天。

`bitable_daily_import._parse_timestamp` 此前按 **UTC** 读取多维表格「时间」列。实测 5 张表的
单元格 ms 恒为 16:00 UTC（= 东八区 00:00），也就是表格里的「2026-10-15」会被存成
``energy_daily_data.date = 2026-10-14`` —— 整张日数据表和由它生成的预警记录都比表格**早一天**。
代码已改为换算到东八区再取日期，这里补齐存量：

1. ``energy.energy_daily_data.date`` 加一天；
2. ``energy.energy_alert_records.alert_time`` 加一天（这些记录全部由 `check_alerts` 生成，
   与日数据同源，必须同步平移，否则反向引用会指向错开的日期）。

用法：
    python scripts/migration/shift_energy_daily_date_to_cst.py            # dry-run（默认，不写库）
    python scripts/migration/shift_energy_daily_date_to_cst.py --apply    # 实际执行

**只能执行一次**：整表平移没有可复用的判据，重复执行会再挪一天。跑错方向可以用
``--days -1 --apply`` 反向补回来。脚本必须在**下一次导入之前**执行；若已经用修好的代码导入过，
平移会撞上 ``uq_energy_daily_data_date_type_category`` 而整个事务回滚，不会留下半套数据。
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402

RANGE_SQL = text(
    """
    SELECT 'energy_daily_data.date' AS target, min(date)::text AS low, max(date)::text AS high, count(*) AS n
    FROM energy.energy_daily_data
    UNION ALL
    SELECT 'energy_alert_records.alert_time', min(alert_time)::text, max(alert_time)::text, count(*)
    FROM energy.energy_alert_records
    """
)

SHIFT_DAILY_SQL = text(
    """
    UPDATE energy.energy_daily_data
    SET date = date + (:days)::int
    """
)

SHIFT_ALERT_SQL = text(
    """
    UPDATE energy.energy_alert_records
    SET alert_time = alert_time + (:days) * interval '1 day'
    """
)


async def run(apply: bool, days: int) -> None:
    async with async_session_factory() as db:
        rows = (await db.execute(RANGE_SQL)).all()
        print(f"平移天数：{days:+d}")
        for target, low, high, n in rows:
            print(f"  {target}: {n} 行，当前范围 {low} ~ {high}")

        if not apply:
            print("dry-run 结束（加 --apply 才写库）")
            return

        await db.execute(SHIFT_DAILY_SQL, {"days": days})
        await db.execute(SHIFT_ALERT_SQL, {"days": days})
        await db.commit()
        print("已提交。之后点「导入数据」，日数据与预警记录的日期应与多维表格一致。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="实际写库，默认只 dry-run")
    parser.add_argument("--days", type=int, default=1, help="平移天数，默认 +1；跑错了用 -1 补回")
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply, days=args.days))
