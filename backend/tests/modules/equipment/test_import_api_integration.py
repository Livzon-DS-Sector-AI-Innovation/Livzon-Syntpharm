"""Integration tests for equipment import v3 API endpoints."""

from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from tests.modules.equipment.conftest import MockDB, _extract_param_values, create_mock_department
from fastapi import FastAPI
from httpx import ASGITransport

from app import main as app_main
from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.hr.models import HrDepartment

# Cast to FastAPI to help mypy understand the type
app_instance = cast(FastAPI, app_main.app)


async def test_preview_returns_inferred_fields() -> None:
    db = MockDB()
    app_instance.dependency_overrides[get_db] = lambda: db
    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    app_instance.dependency_overrides[get_current_user] = lambda: mock_user

    data = [
        {
            "资产编号": "TEST001",
            "资产说明": "测试设备",
            "实物所在部门": "检验室",
            "当前成本": 120000,
            "报废状态": "未报废",
            "资产类别说明": "固定资产.房屋建筑物",
            "数量": 2,
        }
    ]

    mock_dept = create_mock_department("uuid-quality", "质量控制部")

    with patch("app.modules.hr.repository.DepartmentRepository") as mock_repo_class:
        mock_repo = MagicMock()
        mock_repo.get_by_name = AsyncMock(return_value=mock_dept)
        mock_repo_class.return_value = mock_repo

        transport = ASGITransport(app=app_instance)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/equipment/equipments/import/preview", json=data)

        assert response.status_code == 200
        result_data = response.json()
        item = result_data["data"]["items"][0]

        assert item["equipment_class"] == "A"
        assert item["importance"] == "高"
        assert item["status"] == "在用"
        assert item["technical_params"]["数量"] == 2
        assert item["department_name"] == "质量控制部"

    app_instance.dependency_overrides.clear()


async def test_batch_import_handles_null_department() -> None:
    db = MockDB()
    app_instance.dependency_overrides[get_db] = lambda: db
    mock_user = MagicMock()
    mock_user.id = "test-user-id"
    app_instance.dependency_overrides[get_current_user] = lambda: mock_user

    data = [{"资产编号": "TEST002", "资产说明": "未知部门设备", "实物所在部门": "火星分部", "当前成本": 5000}]

    with patch("app.modules.equipment.api.batch_import.repo") as mock_repo:
        mock_repo.get_equipment_by_asset_no = AsyncMock(return_value=None)
        mock_repo.create_equipment = AsyncMock()

        transport = ASGITransport(app=app_instance)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/v1/equipment/equipments/import/batch", json=data)

        assert response.status_code == 200
        result_data = response.json()

        assert result_data["data"]["created_count"] == 1
        call_args = mock_repo.create_equipment.call_args[0][1]
        assert call_args["department_id"] is None
        assert call_args["technical_params"] is None  # No quantity provided

    app_instance.dependency_overrides.clear()
