# mypy: ignore-errors
"""D-46：三条导入链路命中软删行时必须复活，而不是静默留在不可见状态。

唯一约束 uq_energy_monthly_record / uq_energy_daily_data_date_type_category 都不含
is_deleted，所以判重里加 `is_deleted == False` 过滤会让插入分支撞 UniqueViolation；
正确做法是复用同一行并置 is_deleted = False。
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.modules.energy import bitable_cross_import as bci
from app.modules.energy import bitable_daily_import as bdi
from app.modules.energy import repository as repo
from app.modules.energy.models import (
    EnergyAlertRecord,
    EnergyDailyData,
    EnergyMonthlyRecord,
    EnergyWorkshop,
)

RECORD_DATE = date(2026, 10, 1)
RECORD_DATE_MS = 1790812800000  # 2026-10-01 00:00 UTC


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


async def _workshop(db_session, name: str = "测试复活车间") -> EnergyWorkshop:
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


async def test_batch_upsert_revives_soft_deleted_monthly_record(db_session):
    """老飞书导入链路（feishu_import → batch_upsert_monthly_records）。"""
    ws = await _workshop(db_session)
    deleted = EnergyMonthlyRecord(
        workshop_id=ws.id,
        energy_type="electricity",
        record_date=RECORD_DATE,
        value=Decimal(1),
        unit="kWh",
        source="feishu",
        is_deleted=True,
    )
    db_session.add(deleted)
    await db_session.flush()

    created, updated = await repo.batch_upsert_monthly_records(db_session, [_monthly_payload(ws.id, 888)])

    assert created == []
    assert updated == 1
    assert deleted.is_deleted is False
    assert deleted.value == Decimal(888)

    # 复活必须体现在前端读得到的口径上
    records, total = await repo.list_monthly_records(db_session, workshop_id=ws.id)
    assert total == 1
    assert [r.id for r in records] == [deleted.id]


async def test_batch_upsert_inserts_when_no_row_exists(db_session):
    """对照组：无同名行时仍走插入分支，没有把复活逻辑改成唯一行为。"""
    ws = await _workshop(db_session)

    created, updated = await repo.batch_upsert_monthly_records(db_session, [_monthly_payload(ws.id, 100)])

    assert len(created) == 1
    assert updated == 0
    assert created[0].is_deleted is False


def _cross_records(value: int) -> list[dict]:
    """最小月度交叉表：只有 环保中心 的一行电用量。"""
    return [
        {"fields": {"各车间电用量明细": "日期", "列1": "2026-10-01"}},
        {"fields": {"各车间电用量明细": "车间", "列1": "kWh"}},
        {"fields": {"各车间电用量明细": "环保中心(含RTO)", "列1": value}},
    ]


async def test_cross_import_revives_soft_deleted_monthly_record(cross_import, db_session, monkeypatch):
    """新交叉表导入链路（EnergyBitableCrossImport.import_month）。"""
    ws = await cross_import._get_or_create_workshop(db_session, "环保中心(含RTO)")
    deleted = EnergyMonthlyRecord(
        workshop_id=ws.id,
        energy_type="electricity",
        record_date=RECORD_DATE,
        value=Decimal(1),
        unit="kWh",
        source="feishu_bitable",
        is_deleted=True,
    )
    db_session.add(deleted)
    await db_session.flush()

    async def fake_tables():
        return [{"name": "2026-10", "table_id": "tbl-month"}]

    async def fake_records(table_id):
        assert table_id == "tbl-month"
        return _cross_records(1234)

    monkeypatch.setattr(cross_import, "list_tables", fake_tables)
    monkeypatch.setattr(cross_import, "list_records", fake_records)

    result = await cross_import.import_month(db_session, "2026-10")

    assert result["errors"] == []
    assert result["total_updated"] == 1
    assert deleted.is_deleted is False
    assert deleted.value == Decimal(1234)


def _daily_record(total: int) -> dict:
    return {"record_id": "rec1", "fields": {"时间": RECORD_DATE_MS, "类别": "全厂电表", "总数": total, "警戒线": 10}}


async def test_daily_import_revives_soft_deleted_daily_record(daily_import, db_session, monkeypatch):
    """每日数据导入链路（EnergyBitableDailyImport.import_table）。"""
    electricity_table = next(tid for tid, (etype, _) in bdi.TABLE_MAPPING.items() if etype == "electricity")

    deleted = EnergyDailyData(
        date=RECORD_DATE,
        energy_type="electricity",
        category="全厂电表",
        total_value=Decimal(1),
        alert_threshold=Decimal(10),
        source_table="⚡电",
        is_deleted=True,
    )
    db_session.add(deleted)
    await db_session.flush()

    async def fake_records(table_id):
        assert table_id == electricity_table
        return [_daily_record(9)]

    monkeypatch.setattr(daily_import, "list_records", fake_records)

    result = await daily_import.import_table(db_session, electricity_table)

    assert result["errors"] == []
    assert result["total_updated"] == 1
    assert result["total_created"] == 0
    assert deleted.is_deleted is False
    assert deleted.total_value == Decimal(9)


async def test_daily_import_alert_not_duplicated_after_revive(daily_import, db_session, monkeypatch):
    """复活不能重复生成预警：判重键是 alert_record_id，与 is_deleted 无关。"""
    electricity_table = next(tid for tid, (etype, _) in bdi.TABLE_MAPPING.items() if etype == "electricity")
    existing_alert = EnergyAlertRecord(
        energy_type="electricity",
        alert_level="info",
        trigger_value=Decimal(11),
        threshold_value=Decimal(10),
        unit="kWh",
        alert_time=datetime(2026, 10, 1, 23, 59, tzinfo=UTC),
        status="pending",
    )
    db_session.add(existing_alert)
    await db_session.flush()

    deleted = EnergyDailyData(
        date=RECORD_DATE,
        energy_type="electricity",
        category="全厂电表",
        total_value=Decimal(11),
        alert_threshold=Decimal(10),
        source_table="⚡电",
        is_alert=True,
        alert_record_id=existing_alert.id,
        is_deleted=True,
    )
    db_session.add(deleted)
    await db_session.flush()

    async def fake_records(table_id):
        return [_daily_record(15)]

    monkeypatch.setattr(daily_import, "list_records", fake_records)

    await daily_import.import_table(db_session, electricity_table)
    alerts = await daily_import.check_alerts(db_session, RECORD_DATE)

    assert deleted.is_alert is True  # 15 > 警戒线 10，重新导入后仍是预警状态
    assert deleted.alert_record_id == existing_alert.id
    assert alerts == []
