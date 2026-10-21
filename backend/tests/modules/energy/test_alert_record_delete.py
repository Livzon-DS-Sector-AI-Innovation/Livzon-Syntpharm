# mypy: ignore-errors
"""预警记录软删除（`DELETE /api/v1/energy/alerts/records/{record_id}`）的行为契约。

删除置 `is_deleted`，并**清掉** `energy_daily_data.alert_record_id`。多维表格的日数据每天会被修正，
改对之后重新导入应当按新的用量重新判定，所以删除不能永久屏蔽这一行：反向引用一清，
`check_alerts` 的 `alert_record_id IS NULL` 判重就会重新放过它 —— 仍超线则再生成，已被改到线下
则不再生成。因此「删除后仍超线 → 重新生成」和「源数据改对 → 不再生成」两个用例才是本功能的
护栏，其余只是端点契约。
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.energy import bitable_daily_import as bdi
from app.modules.energy import repository as repo
from app.modules.energy.models import EnergyAlertRecord, EnergyDailyData

RECORD_DATE = date(2026, 10, 1)


@pytest.fixture
def daily_import(monkeypatch):
    monkeypatch.setattr(bdi, "FeishuClient", lambda *a, **k: SimpleNamespace())
    return bdi.EnergyBitableDailyImport(app_token="test-token")


async def _alert(db_session) -> EnergyAlertRecord:
    record = EnergyAlertRecord(
        energy_type="electricity",
        alert_level="warning",
        trigger_value=Decimal(15),
        threshold_value=Decimal(10),
        unit="kWh",
        alert_time=datetime(2026, 10, 1, tzinfo=UTC),
        status="pending",
    )
    db_session.add(record)
    await db_session.flush()
    return record


async def _daily(db_session, record: EnergyAlertRecord, *, total: int = 15) -> EnergyDailyData:
    daily = EnergyDailyData(
        date=RECORD_DATE,
        energy_type="electricity",
        category="全厂电表",
        total_value=Decimal(total),
        alert_threshold=Decimal(10),
        source_table="⚡电",
        is_alert=total > 10,
        alert_record_id=record.id,
    )
    db_session.add(daily)
    await db_session.flush()
    return daily


async def test_delete_alert_record_soft_deletes_and_hides_it_from_list(auth_client, db_session):
    record = await _alert(db_session)

    response = await auth_client.delete(f"/api/v1/energy/alerts/records/{record.id}")

    assert response.status_code == 200
    assert response.json()["code"] == 200
    assert record.is_deleted is True

    items, _total = await repo.list_alert_records(db_session, page=1, page_size=20)
    assert record.id not in {item.id for item in items}


async def test_delete_alert_record_keeps_daily_row_but_clears_back_reference(auth_client, db_session):
    """删预警不能连带改动能耗数据本身，但反向引用必须清掉，否则这行永远不再被判重放过。"""
    record = await _alert(db_session)
    daily = await _daily(db_session, record)

    response = await auth_client.delete(f"/api/v1/energy/alerts/records/{record.id}")

    assert response.status_code == 200
    assert daily.is_deleted is False
    assert daily.is_alert is True
    assert daily.total_value == Decimal(15)
    assert daily.alert_record_id is None


async def test_deleted_alert_is_regenerated_while_still_over_threshold(auth_client, db_session, daily_import):
    record = await _alert(db_session)
    daily = await _daily(db_session, record)

    await auth_client.delete(f"/api/v1/energy/alerts/records/{record.id}")
    generated = await daily_import.check_alerts(db_session, RECORD_DATE)

    assert [item["energy_type"] for item in generated] == ["electricity"]
    assert daily.alert_record_id is not None
    assert daily.alert_record_id != record.id
    # `D-50`：alert_time 是数据日的 00:00 UTC，不是 naive 23:59:59（那会被前端按东八区渲染成次日）
    revived = await repo.get_alert_record_by_id(db_session, daily.alert_record_id)
    assert revived is not None
    assert revived.alert_time == datetime(2026, 10, 1, tzinfo=UTC)


async def test_deleted_alert_not_regenerated_after_source_data_fixed(auth_client, db_session, daily_import):
    """源表把用量改到线下后重新导入，不该把预警生回来 —— 判重放开不等于无条件生成。"""
    record = await _alert(db_session)
    daily = await _daily(db_session, record)

    await auth_client.delete(f"/api/v1/energy/alerts/records/{record.id}")
    daily.total_value = Decimal(8)
    daily.is_alert = False
    await db_session.flush()

    assert await daily_import.check_alerts(db_session, RECORD_DATE) == []


async def test_delete_unknown_alert_record_returns_404(auth_client):
    response = await auth_client.delete(f"/api/v1/energy/alerts/records/{uuid4()}")

    assert response.status_code == 404


async def test_delete_already_deleted_alert_record_returns_404(auth_client, db_session):
    record = await _alert(db_session)

    first = await auth_client.delete(f"/api/v1/energy/alerts/records/{record.id}")
    second = await auth_client.delete(f"/api/v1/energy/alerts/records/{record.id}")

    assert first.status_code == 200
    assert second.status_code == 404
