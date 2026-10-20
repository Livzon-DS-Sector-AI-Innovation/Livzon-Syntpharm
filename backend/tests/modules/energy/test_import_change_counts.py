# mypy: ignore-errors
"""D-51：三条导入链路的 `updated` 只统计值真发生变化的行。

SQLAlchemy 只对属性值变化的字段发 UPDATE，所以"匹配到已有行"不等于"更新了该行"。
按匹配数计数会让重复导入永远报「更新 1150 条」（1150 = 表内全部行数），
把"源表没变"误报成"源表全变了"。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.modules.energy import bitable_cross_import as bci
from app.modules.energy import bitable_daily_import as bdi
from app.modules.energy import repository as repo
from app.modules.energy.models import EnergyDailyData, EnergyMonthlyRecord, EnergyWorkshop

RECORD_DATE = date(2026, 9, 1)
RECORD_DATE_MS = 1788220800000  # 2026-09-01 00:00 UTC = 东八区 08:00，取日仍是 09-01


@pytest.fixture
def cross_import(monkeypatch):
    monkeypatch.setattr(bci, "FeishuClient", lambda *a, **k: SimpleNamespace())
    imp = bci.EnergyBitableCrossImport(app_token="test-token")
    imp._alias_map = dict(bci.WORKSHOP_ALIASES)
    return imp


@pytest.fixture
def daily_import(monkeypatch):
    monkeypatch.setattr(bdi, "FeishuClient", lambda *a, **k: SimpleNamespace())
    return bdi.EnergyBitableDailyImport(app_token="test-token")


class _Row:
    def __init__(self, value: Decimal, unit: str) -> None:
        self.value = value
        self.unit = unit


def test_apply_changed_fields_returns_whether_any_value_changed():
    row = _Row(Decimal("1.5"), "kWh")

    assert repo.apply_changed_fields(row, {"value": Decimal("1.50"), "unit": "kWh"}) is False
    assert (row.value, row.unit) == (Decimal("1.5"), "kWh")

    assert repo.apply_changed_fields(row, {"value": Decimal("2"), "unit": "kWh"}) is True
    assert row.value == Decimal("2")


async def _workshop(db_session, name: str) -> EnergyWorkshop:
    ws = EnergyWorkshop(code=name, name=name, category="workshop", sort_order=0, is_active=True)
    db_session.add(ws)
    await db_session.flush()
    return ws


def _monthly_payload(ws_id, value: int) -> dict:
    return {
        "workshop_id": ws_id,
        "energy_type": "electricity",
        "record_date": RECORD_DATE,
        "date_range_end": None,
        "value": Decimal(value),
        "unit": "kWh",
        "source": "feishu",
        "remark": None,
    }


async def test_batch_upsert_counts_only_changed_monthly_rows(db_session):
    ws = await _workshop(db_session, "测试变更计数车间")

    created, updated = await repo.batch_upsert_monthly_records(db_session, [_monthly_payload(ws.id, 100)])
    assert (len(created), updated) == (1, 0)

    # 源表没改：匹配到已有行，但一个字段都没变
    created, updated = await repo.batch_upsert_monthly_records(db_session, [_monthly_payload(ws.id, 100)])
    assert (len(created), updated) == (0, 0)

    # 源表改了那一行：只有它计入变更
    created, updated = await repo.batch_upsert_monthly_records(db_session, [_monthly_payload(ws.id, 101)])
    assert (len(created), updated) == (0, 1)


async def test_batch_upsert_counts_revived_soft_deleted_row_as_changed(db_session):
    """复活本身就是写入，值没变也要算一次变更。"""
    ws = await _workshop(db_session, "测试复活计数车间")
    deleted = EnergyMonthlyRecord(
        workshop_id=ws.id,
        energy_type="electricity",
        record_date=RECORD_DATE,
        value=Decimal(100),
        unit="kWh",
        source="feishu",
        is_deleted=True,
    )
    db_session.add(deleted)
    await db_session.flush()

    created, updated = await repo.batch_upsert_monthly_records(db_session, [_monthly_payload(ws.id, 100)])

    assert (len(created), updated) == (0, 1)
    assert deleted.is_deleted is False


def _daily_record(total: int) -> dict:
    return {"record_id": "rec1", "fields": {"时间": RECORD_DATE_MS, "类别": "全厂电表", "总数": total, "警戒线": 10}}


async def test_daily_import_second_run_reports_zero_updates(daily_import, db_session, monkeypatch):
    electricity_table = next(tid for tid, (etype, _) in bdi.TABLE_MAPPING.items() if etype == "electricity")

    async def fake_records(table_id):
        return [_daily_record(9)]

    monkeypatch.setattr(daily_import, "list_records", fake_records)

    first = await daily_import.import_table(db_session, electricity_table)
    assert (first["total_created"], first["total_updated"]) == (1, 0)

    second = await daily_import.import_table(db_session, electricity_table)
    assert (second["total_created"], second["total_updated"]) == (0, 0)
    assert second["total_parsed"] == 1

    # 源表改了才计一次变更，且写库的值跟着变
    async def changed_records(table_id):
        return [_daily_record(12)]

    monkeypatch.setattr(daily_import, "list_records", changed_records)
    third = await daily_import.import_table(db_session, electricity_table)
    assert third["total_updated"] == 1

    row = (
        await db_session.execute(
            select(EnergyDailyData).where(EnergyDailyData.date == RECORD_DATE, EnergyDailyData.category == "全厂电表")
        )
    ).scalar_one()
    assert row.total_value == Decimal(12)


def _cross_records(value: int) -> list[dict]:
    return [
        {"fields": {"各车间电用量明细": "日期", "列1": "2026-09-01"}},
        {"fields": {"各车间电用量明细": "车间", "列1": "kWh"}},
        {"fields": {"各车间电用量明细": "环保中心(含RTO)", "列1": value}},
    ]


async def test_cross_import_second_run_reports_zero_updates(cross_import, db_session, monkeypatch):
    async def fake_tables():
        return [{"name": "2026-09", "table_id": "tbl-month"}]

    async def fake_records(table_id):
        return _cross_records(1234)

    monkeypatch.setattr(cross_import, "list_tables", fake_tables)
    monkeypatch.setattr(cross_import, "list_records", fake_records)

    first = await cross_import.import_month(db_session, "2026-09")
    assert (first["total_created"], first["total_updated"]) == (1, 0)

    second = await cross_import.import_month(db_session, "2026-09")
    assert (second["total_created"], second["total_updated"]) == (0, 0)
    assert second["total_parsed"] == 1
