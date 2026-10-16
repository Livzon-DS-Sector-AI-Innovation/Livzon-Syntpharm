"""一次性数据修正：预警记录的日期口径与删除后的反向引用。

两件事，都源于 `D-50`：

1. ``alert_time`` 归一到该数据日的 00:00 UTC。历史写入是 ``datetime.combine(date, 23:59:59.999999)``
   这种 **naive** 值，落进 ``timestamp with time zone`` 时被按 UTC 解释，前端再按东八区渲染就整体
   晚了一天（10-13 的数据在列表里显示成 10-14 07:59:59）。预警是按天判定的，时刻没有业务含义，
   所以统一存成当日 00:00 UTC，列表只展示日期。
2. 清掉指向**已软删**预警记录的 ``energy_daily_data.alert_record_id``。删除功能上线初期用的是
   「保留反向引用」口径，那条预警被永久屏蔽；现口径改为「删除即允许重导入时重新判定」，这些行
   得回到可重新生成的状态，否则此前删过的记录永远回不来。

用法：
    python scripts/migration/normalize_energy_alert_time.py            # dry-run（默认，不写库）
    python scripts/migration/normalize_energy_alert_time.py --apply    # 实际执行

脚本可重复执行：第二次运行两项动作都应为 0。
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402

# 待归一的历史值：当日 23:59:59.999999+00（naive 写入的产物）
COUNT_ALERT_TIME_SQL = text(
    """
    SELECT count(*) AS n
    FROM energy.energy_alert_records
    WHERE alert_time <> date_trunc('day', alert_time)
    """
)

APPLY_ALERT_TIME_SQL = text(
    """
    UPDATE energy.energy_alert_records
    SET alert_time = date_trunc('day', alert_time)
    WHERE alert_time <> date_trunc('day', alert_time)
    """
)

# 已软删的预警记录仍被日数据行引用 → 下次导入不会再生成
COUNT_STALE_REF_SQL = text(
    """
    SELECT count(*) AS n
    FROM energy.energy_daily_data d
    JOIN energy.energy_alert_records a ON a.id = d.alert_record_id
    WHERE a.is_deleted
    """
)

APPLY_STALE_REF_SQL = text(
    """
    UPDATE energy.energy_daily_data d
    SET alert_record_id = NULL
    FROM energy.energy_alert_records a
    WHERE d.alert_record_id = a.id
      AND a.is_deleted
    """
)


async def run(apply: bool) -> None:
    async with async_session_factory() as db:
        alert_time_rows = (await db.execute(COUNT_ALERT_TIME_SQL)).scalar_one()
        stale_ref_rows = (await db.execute(COUNT_STALE_REF_SQL)).scalar_one()

        print(f"alert_time 需归一的预警记录：{alert_time_rows}")
        print(f"指向已删预警的日数据行：      {stale_ref_rows}")

        if not apply:
            print("dry-run 结束（加 --apply 才写库）")
            return

        if alert_time_rows:
            await db.execute(APPLY_ALERT_TIME_SQL)
        if stale_ref_rows:
            await db.execute(APPLY_STALE_REF_SQL)
        await db.commit()
        print("已提交。下次「导入数据」时，仍超线的日数据会重新生成预警记录。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="实际写库，默认只 dry-run")
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply))
