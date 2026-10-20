# mypy: ignore-errors
"""AI 能耗分析的生产车间范围限定：只有 9 个生产车间能进单耗分析。

负责人口径：辅助部门与机组的单耗没有业务含义（对不上产品产量），所以 AI 分析板块的车间列表与
分析入口都只允许 `PRODUCTION_WORKSHOPS`。**主数据一行不删**——它们是车间管理页与全厂汇总的
组成行，剔掉总览就对不上多维表格，所以限定只能落在读取侧。
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.exceptions import BadRequestException
from app.modules.energy import service
from app.modules.energy.models import PRODUCTION_WORKSHOPS, EnergyWorkshop

WORKSHOPS_URL = "/api/v1/energy/workshops"
ANALYSIS_URL = "/api/v1/energy/ai-analysis-v2"


@pytest.fixture
def support_workshop(db_session):
    """一个必然不在白名单里的车间（名字带 uuid 后缀，与本地库既有行解耦）。"""
    name = f"辅助部门甲{uuid4().hex[:8]}"
    ws = EnergyWorkshop(code=name, name=name, category="support", sort_order=0, is_active=True)
    db_session.add(ws)
    return ws


async def _live_production_names(db_session) -> set[str]:
    rows = (
        await db_session.execute(
            select(EnergyWorkshop.name).where(
                EnergyWorkshop.is_deleted == False,  # noqa: E712
                EnergyWorkshop.name.in_(sorted(PRODUCTION_WORKSHOPS)),
            )
        )
    ).all()
    return {r[0] for r in rows}


async def _ensure_production_rows(db_session) -> set[str]:
    """补齐库里缺失的白名单车间，让本地（有全量主数据）与 CI（只跑迁移、表为空）都能跑。"""
    existing = await _live_production_names(db_session)
    missing = sorted(PRODUCTION_WORKSHOPS - existing)
    db_session.add_all(
        EnergyWorkshop(code=f"test-{name}", name=name, category="workshop", sort_order=0, is_active=True)
        for name in missing
    )
    await db_session.flush()
    return existing | set(missing)


def test_production_workshop_registry_is_locked():
    """白名单是业务口径，改这行必须经负责人确认，所以先钉住。"""
    assert PRODUCTION_WORKSHOPS == frozenset(
        {
            "101车间",
            "102车间",
            "103车间",
            "105车间",
            "201车间",
            "202车间",
            "301车间",
            "302车间",
            "303、106车间",
        }
    )
    # 名字精确相等才算命中，所以 `103车间` 不会把 `103冷水机组` 放进来
    assert "103冷水机组" not in PRODUCTION_WORKSHOPS
    assert "201盐水机组" not in PRODUCTION_WORKSHOPS


async def test_production_only_filter_returns_only_whitelist(auth_client, db_session, support_workshop):
    await db_session.flush()

    response = await auth_client.get(WORKSHOPS_URL, params={"production_only": True})

    assert response.status_code == 200, response.text
    names = {item["name"] for item in response.json()["data"]}
    assert names <= set(PRODUCTION_WORKSHOPS)
    assert support_workshop.name not in names


async def test_production_only_filter_returns_all_live_production_rows(auth_client, db_session, support_workshop):
    await db_session.flush()
    expected = await _ensure_production_rows(db_session)
    assert expected == set(PRODUCTION_WORKSHOPS), "9 个生产车间都应能进单耗分析"

    response = await auth_client.get(WORKSHOPS_URL, params={"production_only": True})
    names = {item["name"] for item in response.json()["data"]}

    assert names == expected


async def test_workshops_list_without_filter_still_contains_support_rows(auth_client, db_session, support_workshop):
    """对照组：不带 `production_only` 时车间管理页照旧看得到辅助部门，主数据没被动过。"""
    await db_session.flush()

    response = await auth_client.get(WORKSHOPS_URL, params={"category": "support"})

    assert response.status_code == 200, response.text
    names = {item["name"] for item in response.json()["data"]}
    assert support_workshop.name in names


async def test_ai_analysis_v2_rejects_non_production_workshop(auth_client, db_session, support_workshop, monkeypatch):
    from unittest.mock import AsyncMock

    chat_json = AsyncMock()
    monkeypatch.setattr(service.llm_client, "chat_json", chat_json)
    await db_session.flush()

    response = await auth_client.post(
        ANALYSIS_URL,
        json={
            "workshop_id": str(support_workshop.id),
            "analysis_month": "2026-01",
            "production_items": [{"product_name": "某某产品", "quantity": 1, "conversion_factor": 1}],
            "include_ai_suggestion": True,
        },
    )

    assert response.status_code == 400, response.text
    assert "生产车间" in response.text
    # 白名单在取数与调用 LLM 之前就挡住，不会为辅助部门花一次模型调用
    chat_json.assert_not_awaited()


async def test_prepare_data_guard_fires_before_missing_data(db_session, support_workshop):
    """顺序断言：非生产车间报 400，而不是「该月无能耗数据」的 404。"""
    await db_session.flush()

    with pytest.raises(BadRequestException, match="生产车间"):
        await service.prepare_ai_analysis_data(db_session, support_workshop.id, "2026-01", [])


async def test_repo_name_in_filter_is_generic(db_session, support_workshop):
    """`name_in` 是通用读取过滤，不内置业务名；白名单在 service 层解析。"""
    await db_session.flush()

    items, total = await service.repo.list_workshops(db_session, name_in=[support_workshop.name])

    assert total == 1
    assert [w.name for w in items] == [support_workshop.name]

    items, _ = await service.repo.list_workshops(db_session, name_in=[])
    assert items == []
