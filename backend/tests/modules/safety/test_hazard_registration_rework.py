"""隐患登记改造（2026-11）单元测试。

覆盖三处新增逻辑，均不依赖数据库：
1. 整改负责人多选归一化（过滤非法 UUID + 首人回写单人字段 + 空值不清空历史）
2. AI 只补空白（人工已填的隐患等级/类别不被覆盖，旧枚举类别映射为中文类别名）
3. 隐患类别字典合并（内置 7 类与字典项去重）
"""

import uuid
from types import SimpleNamespace
from typing import TYPE_CHECKING, Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.modules.safety.service.hazard import BUILTIN_HAZARD_CATEGORIES, HazardService

if TYPE_CHECKING:
    from app.modules.safety.models import HazardReport


def repo_of(service: HazardService) -> Any:
    """单测里 repo 被替换成 Mock；用 Any 承接，避免 mypy 把 Mock 赋值判成「Cannot assign to a method」。"""
    return service.repo


def make_service() -> HazardService:
    return HazardService(MagicMock())


class TestNormalizeResponsiblePersons:
    """整改负责人多选归一化"""

    def test_filters_invalid_uuid_and_backfills_single_field(self) -> None:
        valid_id = str(uuid.uuid4())
        data = {
            "rectification_responsible_person_ids": [valid_id, "not-a-uuid"],
            "rectification_responsible_person_names": "张三,李四",
        }

        HazardService._normalize_responsible_persons(data, is_create=True)

        assert data["rectification_responsible_person_ids"] == [valid_id]
        assert data["rectification_responsible_person_names"] == "张三,李四"
        # 单人字段回写首人，保证旧的单人字段/通知链路仍可用
        assert str(data["rectification_responsible_person"]) == valid_id
        assert data["rectification_responsible_person_name"] == "张三"

    def test_empty_ids_keeps_name_snapshot_without_binding(self) -> None:
        data: dict[str, Any] = {
            "rectification_responsible_person_ids": [],
            "rectification_responsible_person_names": "张三",
        }

        HazardService._normalize_responsible_persons(data, is_create=False)

        # 姓名无法唯一解析时保留姓名快照（页面显示待确认），但不写任何 UUID
        assert "rectification_responsible_person_ids" not in data
        assert "rectification_responsible_person" not in data
        assert data["rectification_responsible_person_names"] == "张三"
        assert data["rectification_responsible_person_name"] == "张三"

    def test_empty_ids_without_names_does_not_touch_existing_single_field(self) -> None:
        data: dict[str, Any] = {"rectification_responsible_person_ids": []}

        HazardService._normalize_responsible_persons(data, is_create=False)

        assert "rectification_responsible_person" not in data
        assert "rectification_responsible_person_name" not in data

    def test_all_invalid_ids_are_dropped(self) -> None:
        data = {"rectification_responsible_person_ids": ["x", "y"], "rectification_responsible_person_names": "张三"}

        HazardService._normalize_responsible_persons(data, is_create=True)

        assert "rectification_responsible_person_ids" not in data
        assert "rectification_responsible_person" not in data


class TestAiBlankOnly:
    """AI 只补空白"""

    def test_manual_level_and_category_are_not_overwritten(self) -> None:
        service = make_service()
        current = cast(
            "HazardReport",
            SimpleNamespace(
                id=uuid.uuid4(),
                hazard_level="major",
                hazard_category="化学品管理",
            ),
        )
        update_data: dict[str, Any] = {}

        service._map_hazard_ai_output(
            1,
            {"hazard_level": "general", "hazard_category": "equipment", "key_defect": "阀门渗漏"},
            update_data,
            current=current,
        )

        assert "hazard_level" not in update_data
        assert "hazard_category" not in update_data
        # 纯 AI 字段照旧写入
        assert update_data["key_defect"] == "阀门渗漏"

    def test_blank_fields_are_filled_and_legacy_category_mapped(self) -> None:
        service = make_service()
        current = cast(
            "HazardReport",
            SimpleNamespace(id=uuid.uuid4(), hazard_level=None, hazard_category=None),
        )
        update_data: dict[str, Any] = {}

        service._map_hazard_ai_output(
            1,
            {"hazard_level": "general", "hazard_category": "equipment"},
            update_data,
            current=current,
        )

        assert update_data["hazard_level"] == "general"
        assert update_data["hazard_category"] == "设备设施"


class TestHazardCategoryDict:
    """隐患类别字典合并与幂等新增"""

    async def test_list_merges_builtin_and_stored_without_duplicates(self) -> None:
        service = make_service()
        repo = repo_of(service)
        repo.list_hazard_categories = AsyncMock(
            return_value=[
                SimpleNamespace(id=uuid.uuid4(), name="化学品管理", sort_order=100),
                SimpleNamespace(id=uuid.uuid4(), name="特殊作业", sort_order=100),
            ]
        )

        items = await service.list_hazard_categories()
        names = [item["name"] for item in items]

        assert set(BUILTIN_HAZARD_CATEGORIES).issubset(set(names))
        assert names.count("化学品管理") == 1
        assert "特殊作业" in names
        assert len(names) == len(BUILTIN_HAZARD_CATEGORIES) + 1

    async def test_creating_builtin_category_is_idempotent(self) -> None:
        service = make_service()
        repo = repo_of(service)
        repo.get_hazard_category_by_name = AsyncMock()

        item = await service.create_hazard_category("设备设施")

        assert item["is_builtin"] is True
        assert item["name"] == "设备设施"
        repo.get_hazard_category_by_name.assert_not_awaited()

    @pytest.mark.parametrize("name", ["", "   "])
    async def test_blank_name_rejected(self, name: str) -> None:
        service = make_service()

        with pytest.raises(ValueError):
            await service.create_hazard_category(name)
