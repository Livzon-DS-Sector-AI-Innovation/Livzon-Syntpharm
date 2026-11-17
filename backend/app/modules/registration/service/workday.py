"""工作日推算工具。

从中国法定节假日/调休补班日历推算 N 个工作日后的日期。
节假日数据来自 registration.holidays 表（type=holiday / makeup）。
"""

from datetime import date, timedelta

MAX_ITERATION_DAYS = 365 * 3


def is_workday(d: date, holidays: set[date], makeups: set[date]) -> bool:
    """判断是否为工作日：补班日优先，其次周末/节假日排除。"""
    if d in makeups:
        return True
    if d.weekday() >= 5:
        return False
    return d not in holidays


def add_workdays(
    start: date,
    days: int,
    holidays: set[date],
    makeups: set[date],
) -> date:
    """从 start（不含当天）起推算 days 个工作日后的日期。"""
    if days <= 0:
        return start
    d = start
    remaining = days
    iterations = 0
    while remaining > 0:
        d += timedelta(days=1)
        if is_workday(d, holidays, makeups):
            remaining -= 1
        iterations += 1
        if iterations > MAX_ITERATION_DAYS:
            raise ValueError(f"工作日推算超过 {MAX_ITERATION_DAYS} 天，请检查节假日数据")
    return d


def workdays_between(
    start: date,
    end: date,
    holidays: set[date],
    makeups: set[date],
) -> int:
    """计算两个日期之间的工作日数（不含 start，含 end）。end < start 返回负数。"""
    if start == end:
        return 0
    sign = 1
    if end < start:
        start, end = end, start
        sign = -1
    count = 0
    d = start
    while d < end:
        d += timedelta(days=1)
        if is_workday(d, holidays, makeups):
            count += 1
    return sign * count
