# mypy: ignore-errors
"""日数据导入把「时间」列换算成哪一天。

多维表格的日期列按东八区录入：实测 5 张表的原始 ms **全部**满足 ``ms % 86_400_000 == 57_600_000``
（即 16:00 UTC = 东八区 00:00）。按 UTC 取日期会让整张 ``energy_daily_data`` 比表格早一天，
预警记录的日期、以及定时任务 ``check_alerts(db, now.date())`` 要查的那一天都跟着错。
"""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest

from app.modules.energy import bitable_daily_import as bdi


@pytest.fixture
def daily_import(monkeypatch):
    monkeypatch.setattr(bdi, "FeishuClient", lambda *a, **k: SimpleNamespace())
    return bdi.EnergyBitableDailyImport(app_token="test-token")


# 2026-10-14 00:00 东八区，即表格里显示「2026-10-14」的那个单元格
MS_2026_10_14_CST_MIDNIGHT = 1791907200000


def test_parse_timestamp_uses_beijing_calendar_day(daily_import):
    assert daily_import._parse_timestamp(MS_2026_10_14_CST_MIDNIGHT) == date(2026, 10, 14)


def test_parse_record_keeps_the_date_shown_in_the_bitable(daily_import):
    parsed = daily_import._parse_record(
        {"fields": {"时间": MS_2026_10_14_CST_MIDNIGHT, "类别": "全厂电表", "总数": 15, "警戒线": 10}},
        "electricity",
        "⚡电",
    )

    assert parsed is not None
    assert parsed["date"] == date(2026, 10, 14)
