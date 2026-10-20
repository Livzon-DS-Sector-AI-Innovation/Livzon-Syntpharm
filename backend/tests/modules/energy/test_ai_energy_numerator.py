# mypy: ignore-errors
"""AI 单耗的分子只算电（口径见 docs/energy-module-prd.md 6.4，`D-28`）。

`value` 存的是四类能源的裸值（kWh / m³ / t / Nm³），不过滤能源类型直接 SUM 得到的数
没有单位含义，却被当成 kWh 除产量、写进 prompt 与偏差判定。

末段还覆盖 `prepare_ai_analysis_data` 对产量的入口校验（`D-56`）：分子取数与产量折算
共用这条入口，测试车间的种子助手函数已经在上面，不再另开文件。
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.energy import models, service
from app.modules.energy import repository as repo
from app.modules.energy.models import EnergyMonthlyRecord, EnergyWorkshop

# 用远古月份，避免与库中既有月度数据串味
MONTH_START = date(2001, 5, 1)
MONTH_END = date(2001, 6, 1)  # get_monthly_energy_total 的窗口是 [start, end)
ANALYSIS_MONTH = "2001-05"
ANALYSIS_URL = "/api/v1/energy/ai-analysis-v2"


async def _workshop(db, name: str) -> EnergyWorkshop:
    ws = EnergyWorkshop(
        code=f"{name}-{uuid4().hex[:8]}",
        name=name,
        category="workshop",
        sort_order=0,
        is_active=True,
    )
    db.add(ws)
    await db.flush()
    return ws


async def _record(
    db,
    ws: EnergyWorkshop,
    energy_type: str,
    value: float,
    unit: str,
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
        )
    )
    await db.flush()


async def _seed_mixed(db) -> EnergyWorkshop:
    """一个车间、四种能源：电 1000 kWh、水 500 m³、汽 200 t、气 300 Nm³。"""
    ws = await _workshop(db, f"分子口径甲{uuid4().hex[:8]}")
    await _record(db, ws, "electricity", 1000, "kWh")
    await _record(db, ws, "water", 500, "m³", record_date=date(2001, 5, 2))
    await _record(db, ws, "steam", 200, "t", record_date=date(2001, 5, 3))
    await _record(db, ws, "natural_gas", 300, "Nm³", record_date=date(2001, 5, 4))
    return ws


async def _record_only_electric(db) -> EnergyWorkshop:
    """只有电耗的车间：让分子先取到数，把请求推进到产量校验那一步。"""
    ws = await _workshop(db, f"分子只电甲{uuid4().hex[:8]}")
    await _record(db, ws, "electricity", 1000, "kWh")
    return ws


class TestMonthlyTotalEnergyTypeScope:
    async def test_filter_returns_only_electricity(self, db_session) -> None:
        ws = await _seed_mixed(db_session)

        total = await repo.get_monthly_energy_total(
            db_session, ws.id, MONTH_START, MONTH_END, energy_type="electricity"
        )

        assert total == Decimal("1000")

    async def test_without_filter_mixes_bare_values(self, db_session) -> None:
        """对照组：不加过滤就是 `D-28` 的现场——四类裸值相加，和数没有单位含义"""
        ws = await _seed_mixed(db_session)

        total = await repo.get_monthly_energy_total(db_session, ws.id, MONTH_START, MONTH_END)

        assert total == Decimal("2000")

    async def test_soft_deleted_row_not_counted(self, db_session) -> None:
        ws = await _workshop(db_session, f"分子软删甲{uuid4().hex[:8]}")
        await _record(db_session, ws, "electricity", 1000, "kWh")
        db_session.add(
            EnergyMonthlyRecord(
                workshop_id=ws.id,
                energy_type="electricity",
                record_date=date(2001, 5, 9),
                value=Decimal("9000"),
                unit="kWh",
                source="test",
                is_deleted=True,
            )
        )
        await db_session.flush()

        total = await repo.get_monthly_energy_total(
            db_session, ws.id, MONTH_START, MONTH_END, energy_type="electricity"
        )

        assert total == Decimal("1000")


class TestAnalysisNumeratorIsElectricityOnly:
    async def test_prepare_data_uses_electricity_total(self, db_session, monkeypatch) -> None:
        ws = await _seed_mixed(db_session)
        # 白名单按名字精确匹配，测试车间不在业务 9 项里，只放开这一处名字
        monkeypatch.setattr(models, "PRODUCTION_WORKSHOPS", frozenset({ws.name}))

        data = await service.prepare_ai_analysis_data(
            db_session, ws.id, ANALYSIS_MONTH, [{"product_name": f"测试产品{uuid4().hex[:8]}", "quantity": 10}]
        )

        # 分子是 1000 kWh 而不是 2000 的裸值和 → 单耗 100 而不是 200
        assert data["total_energy_kwh"] == 1000.0
        assert data["actual_unit_consumption"] == 100.0

    async def test_workshop_with_only_non_electric_reports_no_data(self, db_session, monkeypatch) -> None:
        """只有水/汽的车间没有电耗，应报「无电耗数据」而不是拿裸值和算出一个单耗"""
        from app.core.exceptions import NotFoundException

        ws = await _workshop(db_session, f"分子无电甲{uuid4().hex[:8]}")
        await _record(db_session, ws, "water", 500, "m³")
        monkeypatch.setattr(models, "PRODUCTION_WORKSHOPS", frozenset({ws.name}))

        with pytest.raises(NotFoundException, match="无电耗数据"):
            await service.prepare_ai_analysis_data(
                db_session, ws.id, ANALYSIS_MONTH, [{"product_name": f"测试产品{uuid4().hex[:8]}", "quantity": 10}]
            )

    async def test_deviation_status_follows_electricity_numerator(self, db_session, monkeypatch) -> None:
        """分子修对之后偏差率与分档才可信：目标 110 时电耗口径是 -9.09%（达标），
        而混加四类裸值得到 200 → +81.82%（critical），一次误判两步。"""
        ws = await _seed_mixed(db_session)
        monkeypatch.setattr(models, "PRODUCTION_WORKSHOPS", frozenset({ws.name}))
        await service.create_target(db_session, ws.id, ANALYSIS_MONTH, 110.0)

        data = await service.prepare_ai_analysis_data(
            db_session, ws.id, ANALYSIS_MONTH, [{"product_name": f"测试产品{uuid4().hex[:8]}", "quantity": 10}]
        )

        assert data["deviation_rate"] == -9.09
        assert data["deviation_status"] == "normal"


class TestZeroProductionIsBadRequest:
    """产量全为 0（前端旧版新增行的默认值）应得到 400，不是 500（`D-56`）。

    抛裸 `ValueError` 会被 `main.py` 的兜底 handler 映射成 500「服务内部错误」，
    把用户输入问题报成服务端故障。
    """

    async def test_zero_quantity_raises_bad_request_with_400(self, db_session, monkeypatch) -> None:
        from app.core.exceptions import BadRequestException

        ws = await _record_only_electric(db_session)
        monkeypatch.setattr(models, "PRODUCTION_WORKSHOPS", frozenset({ws.name}))

        with pytest.raises(BadRequestException, match="折算后总产量必须大于 0") as exc:
            await service.prepare_ai_analysis_data(
                db_session, ws.id, ANALYSIS_MONTH, [{"product_name": f"测试产品{uuid4().hex[:8]}", "quantity": 0}]
            )

        assert exc.value.status_code == 400

    async def test_missing_quantity_key_raises_bad_request(self, db_session, monkeypatch) -> None:
        """quantity 缺省按 0 处理，同样走 400 而不是 TypeError/500"""
        from app.core.exceptions import BadRequestException

        ws = await _record_only_electric(db_session)
        monkeypatch.setattr(models, "PRODUCTION_WORKSHOPS", frozenset({ws.name}))

        with pytest.raises(BadRequestException, match="折算后总产量必须大于 0"):
            await service.prepare_ai_analysis_data(
                db_session, ws.id, ANALYSIS_MONTH, [{"product_name": f"测试产品{uuid4().hex[:8]}"}]
            )

    async def test_endpoint_returns_400_not_500(self, db_session, auth_client, monkeypatch) -> None:
        """HTTP 层：0 产量的请求应是 400 + 可读文案，且守在校验处，不轮到 LLM。"""
        from unittest.mock import AsyncMock

        chat_json = AsyncMock()
        monkeypatch.setattr(service.llm_client, "chat_json", chat_json)

        ws = await _record_only_electric(db_session)
        monkeypatch.setattr(models, "PRODUCTION_WORKSHOPS", frozenset({ws.name}))
        await db_session.flush()

        response = await auth_client.post(
            ANALYSIS_URL,
            json={
                "workshop_id": str(ws.id),
                "analysis_month": ANALYSIS_MONTH,
                "production_items": [{"product_name": "测试产品", "quantity": 0, "conversion_factor": 1}],
                "include_ai_suggestion": True,
            },
        )

        assert response.status_code == 400, response.text
        assert "产量" in response.text
        chat_json.assert_not_awaited()
