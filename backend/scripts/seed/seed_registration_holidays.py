"""Seed 中国法定节假日/调休补班数据到 registration.holidays 表。

数据来源：国务院办公厅关于 2025/2026/2027 年部分节假日安排的通知。
幂等：按 (date, type) 去重，已存在则跳过。

用法：
    docker exec -w /app/backend erp-backend /app/.venv/bin/python scripts/seed/seed_registration_holidays.py
"""

import asyncio
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import select

from app.core.database import async_session_factory
from app.modules.registration.models.drug import Holiday  # noqa: F401

# (起始日期, 结束日期, 描述)，起止均为放假当天（含）
HOLIDAY_RANGES: list[tuple[date, date, str]] = [
    # 2025（国办发明电〔2024〕12号）
    (date(2025, 1, 1), date(2025, 1, 1), "元旦"),
    (date(2025, 1, 28), date(2025, 2, 4), "春节"),
    (date(2025, 4, 4), date(2025, 4, 6), "清明节"),
    (date(2025, 5, 1), date(2025, 5, 5), "劳动节"),
    (date(2025, 5, 31), date(2025, 6, 2), "端午节"),
    (date(2025, 10, 1), date(2025, 10, 8), "国庆节、中秋节"),
    # 2026（国办发明电〔2025〕发布）
    (date(2026, 1, 1), date(2026, 1, 3), "元旦"),
    (date(2026, 2, 15), date(2026, 2, 23), "春节"),
    (date(2026, 4, 4), date(2026, 4, 6), "清明节"),
    (date(2026, 5, 1), date(2026, 5, 5), "劳动节"),
    (date(2026, 6, 19), date(2026, 6, 21), "端午节"),
    (date(2026, 9, 25), date(2026, 9, 27), "中秋节"),
    (date(2026, 10, 1), date(2026, 10, 7), "国庆节"),
    # 2027（国办发明电〔2026〕10号）
    (date(2027, 1, 1), date(2027, 1, 3), "元旦"),
    (date(2027, 2, 5), date(2027, 2, 13), "春节"),
    (date(2027, 4, 3), date(2027, 4, 5), "清明节"),
    (date(2027, 5, 1), date(2027, 5, 5), "劳动节"),
    (date(2027, 6, 9), date(2027, 6, 9), "端午节"),
    (date(2027, 9, 15), date(2027, 9, 15), "中秋节"),
    (date(2027, 10, 1), date(2027, 10, 7), "国庆节"),
]

# 调休补班日（周末上班）
MAKEUP_DAYS: list[tuple[date, str]] = [
    # 2025
    (date(2025, 1, 26), "春节调休补班"),
    (date(2025, 2, 8), "春节调休补班"),
    (date(2025, 4, 27), "劳动节调休补班"),
    (date(2025, 9, 28), "国庆节、中秋节调休补班"),
    (date(2025, 10, 11), "国庆节、中秋节调休补班"),
    # 2026
    (date(2026, 1, 4), "元旦调休补班"),
    (date(2026, 2, 14), "春节调休补班"),
    (date(2026, 2, 28), "春节调休补班"),
    (date(2026, 5, 9), "劳动节调休补班"),
    (date(2026, 9, 20), "国庆节调休补班"),
    (date(2026, 10, 10), "国庆节调休补班"),
    # 2027
    (date(2027, 1, 31), "春节调休补班"),
    (date(2027, 2, 14), "春节调休补班"),
    (date(2027, 5, 8), "劳动节调休补班"),
    (date(2027, 9, 26), "国庆节调休补班"),
    (date(2027, 10, 9), "国庆节调休补班"),
]


def _expand_ranges() -> list[tuple[date, str]]:
    days: list[tuple[date, str]] = []
    for start, end, desc in HOLIDAY_RANGES:
        d = start
        while d <= end:
            days.append((d, desc))
            d += timedelta(days=1)
    return days


async def main() -> None:
    entries = [(d, "holiday", desc) for d, desc in _expand_ranges()]
    entries += [(d, "makeup", desc) for d, desc in MAKEUP_DAYS]

    async with async_session_factory() as session:
        existing_result = await session.execute(select(Holiday.date, Holiday.type))
        existing = {(row.date, row.type) for row in existing_result.all()}

        inserted = 0
        for d, type_, desc in entries:
            if (d, type_) in existing:
                continue
            session.add(Holiday(year=d.year, date=d, type=type_, description=desc))
            inserted += 1

        await session.commit()

    holiday_count = len(_expand_ranges())
    print(f"完成：新增 {inserted} 条（节假日 {holiday_count} 天 + 补班日 {len(MAKEUP_DAYS)} 天，已存在的跳过）")


if __name__ == "__main__":
    asyncio.run(main())
