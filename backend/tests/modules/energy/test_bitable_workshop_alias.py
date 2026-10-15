# mypy: ignore-errors
"""交叉表导入器的车间别名与软删除行为。"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import func, select

from app.modules.energy import bitable_cross_import as bci
from app.modules.energy.models import EnergyWorkshop


async def _active_count(db, name: str) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(EnergyWorkshop)
            .where(EnergyWorkshop.name == name, EnergyWorkshop.is_deleted == False)  # noqa: E712
        )
    ) or 0


@pytest.fixture
def cross_import(monkeypatch):
    monkeypatch.setattr(bci, "FeishuClient", lambda *a, **k: SimpleNamespace())
    imp = bci.EnergyBitableCrossImport(app_token="test-token")
    imp._alias_map = dict(bci.WORKSHOP_ALIASES)
    return imp


def test_shared_meter_name_is_no_longer_truncated(cross_import):
    assert cross_import._normalize_workshop_name("303、106车间") == "303、106车间"
    assert cross_import._normalize_workshop_name("101") == "101车间"


async def test_alias_reuses_canonical_workshop(cross_import, db_session):
    cross_import._alias_map = {"别名甲": "规范甲"}
    canonical = EnergyWorkshop(code="规范甲", name="规范甲", category="support", sort_order=0, is_active=True)
    db_session.add(canonical)
    await db_session.flush()

    resolved = await cross_import._get_or_create_workshop(db_session, "别名甲")

    assert resolved.id == canonical.id
    assert await _active_count(db_session, "别名甲") == 0


async def test_soft_deleted_workshop_is_not_reused(cross_import, db_session):
    """编码唯一约束只认 code，软删除行的 code 仍占位，因此这里用不同 code 模拟 feishu_import 生成的编码。"""
    cross_import._alias_map = {"别名乙": "规范乙"}
    deleted = EnergyWorkshop(
        code="WSABC123", name="规范乙", category="support", sort_order=0, is_active=True, is_deleted=True
    )
    db_session.add(deleted)
    await db_session.flush()

    fresh = await cross_import._get_or_create_workshop(db_session, "别名乙")

    assert fresh.id != deleted.id
    assert fresh.name == "规范乙"
    assert fresh.is_deleted is False


async def test_water_and_electricity_labels_resolve_to_one_entity(cross_import, db_session):
    """水侧写 303、106、电/汽侧写 303、106车间，必须落到同一个车间实体。"""
    from_elec = await cross_import._get_or_create_workshop(db_session, "303、106车间")
    from_water = await cross_import._get_or_create_workshop(db_session, "303、106")
    await db_session.flush()

    assert from_elec.id == from_water.id
    assert from_elec.name == "303、106车间"


async def _active_total(db) -> int:
    return (
        await db.scalar(select(func.count()).select_from(EnergyWorkshop).where(EnergyWorkshop.is_deleted == False))  # noqa: E712
    ) or 0


async def test_environment_center_water_and_electricity_labels_resolve_to_one_entity(cross_import, db_session):
    """水侧写 废水站、电侧写 环保中心(含RTO)、汽侧写 环保中心，三者必须是同一个车间实体。"""
    before = await _active_total(db_session)

    from_water = await cross_import._get_or_create_workshop(db_session, "废水站")
    from_elec = await cross_import._get_or_create_workshop(db_session, "环保中心(含RTO)")
    from_steam = await cross_import._get_or_create_workshop(db_session, "环保中心")
    await db_session.flush()

    assert from_water.id == from_elec.id == from_steam.id
    assert from_water.name == "环保中心"

    # 三种叫法都不该催生新车间（废水站 这个实体由迁移脚本负责合并掉）
    assert await _active_total(db_session) == before


async def test_mapping_sheet_overrides_builtin_constant(cross_import, monkeypatch):
    async def fake_tables():
        return [{"name": bci.MAPPING_TABLE_NAME, "table_id": "tbl-map"}]

    async def fake_records(table_id):
        assert table_id == "tbl-map"
        return [{"fields": {"名称": "分析中心", "别名": "QC、检验科"}}]

    monkeypatch.setattr(cross_import, "list_tables", fake_tables)
    monkeypatch.setattr(cross_import, "list_records", fake_records)
    cross_import._alias_map = None

    alias_map = await cross_import._get_alias_map()

    assert alias_map["QC"] == "分析中心"
    assert alias_map["检验科"] == "分析中心"
    assert alias_map["炊事班"] == "饭堂"


async def test_missing_mapping_sheet_falls_back_to_constant(cross_import, monkeypatch):
    async def fake_tables():
        return [{"name": "2026-09", "table_id": "tbl-09"}]

    async def fail_records(table_id):
        raise AssertionError("缺映射表时不应再请求记录")

    monkeypatch.setattr(cross_import, "list_tables", fake_tables)
    monkeypatch.setattr(cross_import, "list_records", fail_records)
    cross_import._alias_map = None

    assert await cross_import._get_alias_map() == dict(bci.WORKSHOP_ALIASES)
