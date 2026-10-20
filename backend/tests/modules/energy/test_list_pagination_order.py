# mypy: ignore-errors
"""分页列表的排序必须是全序，否则同一行会在第 1 页和第 2 页重复出现。

月度列表原先只按 `record_date DESC` 排：交叉表一次写入几十条，record_date 完全并列，
Postgres 不保证并列行的顺序，于是「动力运行」这类车间会在翻页时重复显示（筛选车间或日期
后只剩一页，看起来就正常了）。预警列表在 `alert_time` 归一到日之后是同样的形状。

用例用库里的哨兵日期把行隔离出来，并用固定 UUID 让期望顺序与插入顺序错开。
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from app.modules.energy import repository as repo
from app.modules.energy.models import EnergyAlertRecord, EnergyMonthlyRecord, EnergyWorkshop

# 不会出现在真实能耗数据里的日期，用来把本用例的行与共享库里的存量行隔开
SENTINEL_DAY = date(2099, 1, 1)
SENTINEL_START = datetime(2099, 1, 1, tzinfo=UTC)
SENTINEL_END = datetime(2099, 1, 1, 23, 59, 59, tzinfo=UTC)

WS_A = UUID(int=1)
WS_B = UUID(int=2)


async def _workshops(db_session) -> None:
    for ws_id, name in ((WS_A, "车间A"), (WS_B, "车间B")):
        db_session.add(
            EnergyWorkshop(id=ws_id, code=name, name=name, category="workshop", sort_order=0, is_active=True)
        )
    await db_session.flush()


async def _monthly(db_session, seq: int, workshop_id: UUID, energy_type: str) -> None:
    db_session.add(
        EnergyMonthlyRecord(
            id=UUID(int=100 + seq),
            workshop_id=workshop_id,
            energy_type=energy_type,
            record_date=SENTINEL_DAY,
            value=Decimal(1),
            unit="kWh",
            source="feishu_bitable",
        )
    )
    await db_session.flush()


async def test_list_monthly_records_orders_tied_dates_deterministically(db_session):
    await _workshops(db_session)
    # 故意按与期望相反的形状插入，让排序键而不是插入顺序决定结果
    await _monthly(db_session, 1, WS_B, "water")
    await _monthly(db_session, 2, WS_A, "water")
    await _monthly(db_session, 3, WS_B, "electricity")
    await _monthly(db_session, 4, WS_A, "electricity")

    kwargs = {"start_date": SENTINEL_DAY, "end_date": SENTINEL_DAY}
    page_1, total = await repo.list_monthly_records(db_session, page=1, page_size=2, **kwargs)
    page_2, _ = await repo.list_monthly_records(db_session, page=2, page_size=2, **kwargs)

    assert total == 4
    assert [(r.workshop_id, r.energy_type) for r in page_1 + page_2] == [
        (WS_A, "electricity"),
        (WS_A, "water"),
        (WS_B, "electricity"),
        (WS_B, "water"),
    ]


async def _alert(db_session, seq: int, energy_type: str) -> None:
    db_session.add(
        EnergyAlertRecord(
            id=UUID(int=200 + seq),
            energy_type=energy_type,
            alert_level="warning",
            trigger_value=Decimal(15),
            threshold_value=Decimal(10),
            unit="",
            alert_time=SENTINEL_START,
            status="pending",
        )
    )
    await db_session.flush()


async def test_list_alert_records_orders_tied_days_deterministically(db_session):
    await _alert(db_session, 1, "water")
    await _alert(db_session, 2, "electricity")
    await _alert(db_session, 3, "water")

    items, total = await repo.list_alert_records(
        db_session, start_time=SENTINEL_START, end_time=SENTINEL_END, page=1, page_size=10
    )

    assert total == 3
    assert [(r.energy_type, r.id) for r in items] == [
        ("electricity", UUID(int=202)),
        ("water", UUID(int=201)),
        ("water", UUID(int=203)),
    ]
