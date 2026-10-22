# mypy: ignore-errors
"""总览「今日」窗口按东八区换算，软删车间不再计入统计或出现在月度列表。"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

import pytest

from app.core.exceptions import BadRequestException
from app.modules.energy import repository as repo
from app.modules.energy import service
from app.modules.energy.models import EnergyMonthlyRecord, EnergyWorkshop

DAY = date(2099, 2, 2)
PREVIOUS_DAY = date(2099, 2, 1)
# 东八区 2099-02-02 全天对应的 UTC 窗口（前端把本地零点 toISOString 后就是这个形状）
WINDOW_START = datetime(2099, 2, 1, 16, 0, tzinfo=UTC)
WINDOW_END = datetime(2099, 2, 2, 15, 59, 59, tzinfo=UTC)


def test_cst_date_maps_utc_midnight_to_next_local_day():
    assert repo._cst_date(WINDOW_START) == DAY
    assert repo._cst_date(WINDOW_END) == DAY


async def _seed(db_session) -> None:
    active = EnergyWorkshop(
        id=UUID(int=301), code="时区车间A", name="时区车间A", category="workshop", sort_order=0, is_active=True
    )
    deleted = EnergyWorkshop(
        id=UUID(int=302),
        code="时区车间B",
        name="时区车间B",
        category="workshop",
        sort_order=0,
        is_active=True,
        is_deleted=True,
    )
    db_session.add_all([active, deleted])
    await db_session.flush()

    rows = [
        (active.id, DAY, Decimal(10)),
        (deleted.id, DAY, Decimal(100)),
        # 前一天的数据用于证明窗口没有跨天
        (active.id, PREVIOUS_DAY, Decimal(1000)),
    ]
    for seq, (workshop_id, record_date, value) in enumerate(rows, start=1):
        db_session.add(
            EnergyMonthlyRecord(
                id=UUID(int=400 + seq),
                workshop_id=workshop_id,
                energy_type="electricity",
                record_date=record_date,
                value=value,
                unit="kWh",
                source="feishu_bitable",
            )
        )
    await db_session.flush()


async def test_overview_summary_uses_cst_day_and_skips_deleted_workshop(db_session):
    await _seed(db_session)

    rows = await repo.get_overview_summary(db_session, WINDOW_START, WINDOW_END)

    assert [(r["energy_type"], r["total_value"]) for r in rows] == [("electricity", 10.0)]


async def test_monthly_list_filters_deleted_workshop_and_returns_name(db_session):
    await _seed(db_session)

    records, total = await repo.list_monthly_records(
        db_session, start_date=DAY, end_date=DAY, page=1, page_size=10
    )

    assert total == 1
    assert records[0].value == Decimal(10)
    assert getattr(records[0], "workshop_name") == "时区车间A"


async def test_monthly_summary_skips_deleted_workshop(db_session):
    await _seed(db_session)

    summary = await repo.get_monthly_summary(db_session, start_date=DAY, end_date=DAY)

    assert summary["electricity"]["total_value"] == 10.0


async def test_delete_workshop_with_monthly_records_is_rejected(db_session):
    await _seed(db_session)

    with pytest.raises(BadRequestException):
        await service.delete_workshop(db_session, UUID(int=301))

    assert await repo.get_workshop_by_id(db_session, UUID(int=301)) is not None


async def test_delete_workshop_without_monthly_records_succeeds(db_session):
    workshop = EnergyWorkshop(
        id=UUID(int=303),
        code="时区车间C",
        name="时区车间C",
        category="workshop",
        sort_order=0,
        is_active=True,
    )
    db_session.add(workshop)
    await db_session.flush()

    await service.delete_workshop(db_session, workshop.id)

    assert await repo.get_workshop_by_id(db_session, workshop.id) is None
