# mypy: ignore-errors
"""全厂汇总剔除合计行（避免重复计数）与月度明细口径的边界。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.energy import bitable_cross_import as bci
from app.modules.energy import repository as repo
from app.modules.energy.models import EnergyMonthlyRecord, EnergyWorkshop

# 用远古月份，避免与库中既有月度数据串味
MONTH_START = date(2001, 5, 1)
MONTH_END = date(2001, 5, 31)
DT_START = datetime(2001, 5, 1)
DT_END = datetime(2001, 5, 31)

ROLLUP = "合计行甲"
COMPONENTS = ("部件甲", "部件乙")
CONTAINER = "容器甲"
MEMBER = "成员甲"


async def _workshop(db, name: str, excluded: tuple[str, ...] = ()) -> EnergyWorkshop:
    ws = EnergyWorkshop(
        code=f"{name}-{uuid4().hex[:8]}",
        name=name,
        category="workshop",
        sort_order=0,
        is_active=True,
        excluded_energy_types=list(excluded),
    )
    db.add(ws)
    await db.flush()
    return ws


async def _record(
    db,
    ws: EnergyWorkshop,
    energy_type: str,
    value: float,
    unit: str = "kWh",
    is_deleted: bool = False,
    record_date: date = MONTH_START,
) -> None:
    db.add(
        EnergyMonthlyRecord(
            workshop_id=ws.id,
            energy_type=energy_type,
            record_date=record_date,
            value=Decimal(str(value)),
            unit=unit,
            source="test",
            is_deleted=is_deleted,
        )
    )
    await db.flush()


@pytest.fixture
def cross_import(monkeypatch):
    monkeypatch.setattr(bci, "FeishuClient", lambda *a, **k: SimpleNamespace())
    monkeypatch.setattr(bci, "ROLLUP_WORKSHOPS", {ROLLUP: ("electricity",), MEMBER: ("electricity",)})
    monkeypatch.setattr(bci, "ROLLUP_COMPONENTS", {ROLLUP: ("electricity", COMPONENTS)})
    monkeypatch.setattr(bci, "ROLLUP_CONTAINERS", {CONTAINER: ("electricity", MEMBER)})
    imp = bci.EnergyBitableCrossImport(app_token="test-token")
    imp._alias_map = dict(bci.WORKSHOP_ALIASES)
    return imp


async def test_overview_summary_excludes_only_marked_type(db_session):
    """同一车间只剔被标记的能源类型：电剔除、气保留。"""
    marked = await _workshop(db_session, ROLLUP, excluded=("electricity",))
    plain = await _workshop(db_session, "普通车间甲")
    await _record(db_session, marked, "electricity", 1000)
    await _record(db_session, marked, "natural_gas", 7, unit="Nm³")
    await _record(db_session, plain, "electricity", 500)

    overview = await repo.get_overview_summary(db_session, DT_START, DT_END)
    summary = {s["energy_type"]: s["total_value"] for s in overview}

    assert summary["electricity"] == 500
    assert summary["natural_gas"] == 7


async def test_statistics_and_trend_use_same_exclusion(db_session):
    marked = await _workshop(db_session, ROLLUP, excluded=("electricity",))
    plain = await _workshop(db_session, "普通统计甲")
    await _record(db_session, marked, "electricity", 1000)
    await _record(db_session, plain, "electricity", 500)

    stats = await repo.get_energy_statistics(
        db_session, group_by="workshop", start_time=DT_START, end_time=DT_END, energy_type="electricity"
    )
    assert {r["group_key"] for r in stats} == {"普通统计甲"}

    trend = await repo.get_overview_trend(db_session, DT_START, DT_END, energy_type="electricity")
    assert sum(t["value"] for t in trend) == 500


async def test_monthly_summary_excludes_company_wide_only(db_session):
    """全公司口径剔除；按车间查询保留其自身上报值（月度记录页仍要看得到）。"""
    rollup = await _workshop(db_session, ROLLUP, excluded=("electricity",))
    plain = await _workshop(db_session, "普通汇总甲")
    await _record(db_session, rollup, "electricity", 1000)
    await _record(db_session, plain, "electricity", 500)

    company = await repo.get_monthly_summary(db_session, start_date=MONTH_START, end_date=MONTH_END)
    assert company["electricity"]["total_value"] == 500

    single = await repo.get_monthly_summary(
        db_session, workshop_id=rollup.id, start_date=MONTH_START, end_date=MONTH_END
    )
    assert single["electricity"]["total_value"] == 1000


async def test_monthly_summary_ignores_soft_deleted(db_session):
    ws = await _workshop(db_session, "软删汇总甲")
    await _record(db_session, ws, "electricity", 100)
    # 同 (车间, 类型, 日期) 受 uq_energy_monthly_record 约束，软删行只能落在别的日子
    await _record(db_session, ws, "electricity", 999, is_deleted=True, record_date=MONTH_END)

    company = await repo.get_monthly_summary(db_session, start_date=MONTH_START, end_date=MONTH_END)
    assert company["electricity"]["total_value"] == 100


async def test_single_workshop_total_not_excluded(db_session):
    """单车间口径（AI 单耗分析）必须保留自身上报值。"""
    rollup = await _workshop(db_session, "单耗口径甲", excluded=("electricity",))
    await _record(db_session, rollup, "electricity", 1000)

    total = await repo.get_monthly_energy_total(db_session, rollup.id, MONTH_START, MONTH_END)
    assert total == Decimal("1000")


async def test_importer_marks_new_rollup_workshop(cross_import, db_session):
    """重建合计行车间时自动补回标记，否则全厂汇总又会重复计数。"""
    ws = await cross_import._get_or_create_workshop(db_session, ROLLUP)
    assert ws.excluded_energy_types == ["electricity"]


async def test_importer_does_not_mark_normal_workshop(cross_import, db_session):
    ws = await cross_import._get_or_create_workshop(db_session, "普通新建甲")
    assert ws.excluded_energy_types == []


async def test_importer_keeps_manual_unmark(cross_import, db_session):
    """人工在车间管理页取消标记后，导入不得覆盖。"""
    existing = await _workshop(db_session, ROLLUP)
    resolved = await cross_import._get_or_create_workshop(db_session, ROLLUP)
    assert resolved.id == existing.id
    assert resolved.excluded_energy_types == []


async def _seed(db_session, rollup_value: float, component_value: float) -> None:
    rollup = await _workshop(db_session, ROLLUP, excluded=("electricity",))
    await _record(db_session, rollup, "electricity", rollup_value)
    for name in COMPONENTS:
        await _record(db_session, await _workshop(db_session, name), "electricity", component_value)


async def test_consistency_warning_fires_on_deviation(cross_import, db_session):
    await _seed(db_session, rollup_value=1000, component_value=100)

    warnings = await cross_import._check_rollup_consistency(db_session, [{"record_date": MONTH_START}])

    assert any(ROLLUP in w for w in warnings)


async def test_consistency_warning_silent_when_matching(cross_import, db_session):
    await _seed(db_session, rollup_value=200, component_value=100)

    warnings = await cross_import._check_rollup_consistency(db_session, [{"record_date": MONTH_START}])

    assert not any(ROLLUP in w for w in warnings)


async def test_container_smaller_than_member_warns(cross_import, db_session):
    container = await _workshop(db_session, CONTAINER)
    member = await _workshop(db_session, MEMBER, excluded=("electricity",))
    await _record(db_session, container, "electricity", 100)
    await _record(db_session, member, "electricity", 900)

    warnings = await cross_import._check_rollup_consistency(db_session, [{"record_date": MONTH_START}])

    assert any(CONTAINER in w for w in warnings)


async def test_no_records_returns_no_warning(cross_import, db_session):
    assert await cross_import._check_rollup_consistency(db_session, []) == []


OVERVIEW_PARAMS = {"start_time": "2001-05-01T00:00:00", "end_time": "2001-05-31T23:59:59"}


async def test_overview_api_excludes_rollup_types(auth_client, db_session):
    """总览三个区块（汇总卡片/趋势/区域分布）都必须走同一剔除口径。"""
    marked = await _workshop(db_session, ROLLUP, excluded=("electricity",))
    plain = await _workshop(db_session, "普通总览甲")
    await _record(db_session, marked, "electricity", 1000)
    await _record(db_session, marked, "natural_gas", 7, unit="Nm³")
    await _record(db_session, plain, "electricity", 500)

    resp = await auth_client.get("/api/v1/energy/overview", params=OVERVIEW_PARAMS)
    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]

    assert data["summary"]["total_electricity"] == 500
    assert data["summary"]["total_natural_gas"] == 7
    assert {d["group_key"] for d in data["distribution"] if d["energy_type"] == "electricity"} == {"普通总览甲"}
    assert sum(t["value"] for t in data["trend"] if t["type"] == "electricity") == 500


async def test_workshop_api_roundtrip_excluded_types(auth_client):
    payload = {
        "code": f"ROLLUP-{uuid4().hex[:6]}",
        "name": "接口合计行甲",
        "category": "utility",
        "excluded_energy_types": ["electricity"],
    }
    created = await auth_client.post("/api/v1/energy/workshops", json=payload)
    assert created.status_code == 200, created.text
    body = created.json()["data"]
    assert body["excluded_energy_types"] == ["electricity"]

    detail = await auth_client.get(f"/api/v1/energy/workshops/{body['id']}")
    assert detail.json()["data"]["excluded_energy_types"] == ["electricity"]

    cleared = await auth_client.put(f"/api/v1/energy/workshops/{body['id']}", json={"excluded_energy_types": []})
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["data"]["excluded_energy_types"] == []


async def test_real_workshop_names_are_registered():
    """生产库里的合计行实体名与常量必须一致，改名会让剔除静默失效。"""
    assert set(bci.ROLLUP_WORKSHOPS) == {"动力运行", "RTO"}
    assert bci.ROLLUP_COMPONENTS["动力运行"][1] == (
        "201盐水机组",
        "103冷水机组",
        "4号楼冷水机组",
        "500T冷水机组",
        "500T盐水机组",
        "空压氮气系统",
    )
