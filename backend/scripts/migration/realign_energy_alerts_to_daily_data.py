"""一次性数据修正：软删「触发值与当日实际用量不一致」的预警记录，并放开反向引用。

背景：`D-52` 之前 `_parse_timestamp` 按 UTC 读多维表格「时间」列，`check_alerts` 于是把
**第二天**的用量记到了前一天头上。代码修好后做一次全量重导入，`energy_daily_data` 的日期与数值
会原地自愈，但 `check_alerts` 只在 `alert_record_id IS NULL` 时新建、从不改写已生成的记录
（`bitable_daily_import.py:233`），所以那批错位记录被永久留在错日子上：触发值是别的某一天的数，
其中一部分挂的日子实际根本没到警戒线（幻影预警）。自愈还会让每段连续超标的**最后一天**
新出一条正确记录，与前一天的错位记录数值相同，在列表里看着像重复。

判定口径只有一条：live 记录的 `trigger_value` 与「该记录日期对应的那条 live 日数据」的
`total_value` 不一致，就软删它，然后把指向已删记录的反向引用置回 NULL，让下一次导入按
现在正确的日数据重新判定。

用法：
    python scripts/migration/realign_energy_alerts_to_daily_data.py            # dry-run（默认，不写库）
    python scripts/migration/realign_energy_alerts_to_daily_data.py --apply    # 实际执行

跑完必须点一次页面「导入数据」（`POST /api/v1/energy/sync/bitable/daily-import`）—— 它会枚举所有
「超标且未挂记录」的日期逐日重建预警，历史月份也补得回来。定时任务只查东八区当天，补不了历史。

可重复执行：重建后的记录与当日数值一致，第二次跑是 0 行。若存量还停在「日期整体早一天」且从未
重导入过的状态（比如 UAT 未跑过修好的代码），本脚本也不会误删——那种情况下记录与所在日的
日数据是自洽的，该先用 `shift_energy_daily_date_to_cst.py` 修日期。
"""

import argparse
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text  # noqa: E402

from app.core.database import async_session_factory  # noqa: E402

PREVIEW_SQL = text(
    """
    SELECT a.energy_type, count(*) AS n
    FROM energy.energy_alert_records a
    JOIN energy.energy_daily_data d
      ON d.energy_type = a.energy_type AND d.is_deleted = false
     AND d.date = (a.alert_time AT TIME ZONE 'UTC')::date
    WHERE a.is_deleted = false AND a.trigger_value IS DISTINCT FROM d.total_value
    GROUP BY 1 ORDER BY 1
    """
)

INVARIANT_SQL = text(
    """
    SELECT count(*) FILTER (WHERE d.is_deleted = false AND d.is_alert AND d.alert_record_id IS NULL) AS unlinked_over,
           count(*) FILTER (WHERE a.is_deleted = false) AS live_records,
           count(*) FILTER (
               WHERE a.is_deleted = false AND d.is_deleted = false AND a.trigger_value = d.total_value
           ) AS live_matching
    FROM energy.energy_alert_records a
    LEFT JOIN energy.energy_daily_data d
      ON d.energy_type = a.energy_type AND d.date = (a.alert_time AT TIME ZONE 'UTC')::date
    """
)

MARK_DELETED_SQL = text(
    """
    UPDATE energy.energy_alert_records a
    SET is_deleted = true
    WHERE a.is_deleted = false
      AND a.id IN (
        SELECT a2.id
        FROM energy.energy_alert_records a2
        JOIN energy.energy_daily_data d2
          ON d2.energy_type = a2.energy_type AND d2.is_deleted = false
         AND d2.date = (a2.alert_time AT TIME ZONE 'UTC')::date
        WHERE a2.trigger_value IS DISTINCT FROM d2.total_value
      )
    """
)

CLEAR_REFS_SQL = text(
    """
    UPDATE energy.energy_daily_data d
    SET alert_record_id = NULL
    WHERE d.alert_record_id IS NOT NULL
      AND NOT EXISTS (
        SELECT 1 FROM energy.energy_alert_records a
        WHERE a.id = d.alert_record_id AND a.is_deleted = false
      )
    """
)


async def run(apply: bool) -> None:
    async with async_session_factory() as db:
        stale = (await db.execute(PREVIEW_SQL)).all()
        total = sum(n for _, n in stale)
        print(f"待软删的错位预警：{total} 条")
        for energy_type, n in stale:
            print(f"  {energy_type}: {n}")
        if not stale:
            print("（没有错位记录，脚本无需执行）")
        inv = (await db.execute(INVARIANT_SQL)).mappings().one()
        print(
            f"当前：live {inv['live_records']} 条，数值与当日一致 {inv['live_matching']} 条，"
            f"超标但未挂记录 {inv['unlinked_over']} 条"
        )

        if not apply:
            print("dry-run 结束（加 --apply 才写库）")
            return

        deleted = await db.execute(MARK_DELETED_SQL)
        cleared = await db.execute(CLEAR_REFS_SQL)
        await db.commit()
        print(f"已软删 {deleted.rowcount} 条预警，清空 {cleared.rowcount} 条反向引用。")  # type: ignore[attr-defined]
        print("下一步：点页面「导入数据」按当日实际用量重建预警，历史漏报会一并补回。")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="实际写库，默认只 dry-run")
    args = parser.parse_args()
    asyncio.run(run(apply=args.apply))
