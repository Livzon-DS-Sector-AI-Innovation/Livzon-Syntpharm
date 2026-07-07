import asyncio
from typing import Any
from uuid import uuid4

import pytest

from app.core.exceptions import AppException
from app.modules.warehouse import service as warehouse_service
from app.modules.warehouse.models import WarehouseFeishuConfig, WarehouseFeishuTable
from app.modules.warehouse.service import WarehouseService


def test_config_app_tokens_uses_three_business_domains_with_legacy_fallback() -> None:
    config = WarehouseFeishuConfig(
        config_name="仓储飞书配置",
        app_id="cli_123",
        encrypted_app_secret="encrypted",
        bitable_app_token="legacy_base",
        finished_product_app_token="product_base",
        materials_packaging_app_token=None,
        hardware_app_token="hardware_base",
        is_active=True,
    )

    tokens = WarehouseService._config_app_tokens(config)

    assert tokens == {
        "finished_product": "product_base",
        "materials_packaging": "legacy_base",
        "hardware": "hardware_base",
    }


def test_build_search_text_flattens_nested_feishu_fields() -> None:
    text = WarehouseService._build_search_text(
        {
            "名称": [{"text": "阿莫西林"}],
            "库存": 12,
            "负责人": {"name": "张三", "email": "demo@example.com"},
        }
    )

    assert "名称" in text
    assert "阿莫西林" in text
    assert "12" in text
    assert "张三" in text
    assert "demo@example.com" in text


class FakeRecordClient:
    def __init__(self) -> None:
        self.calls: list[str | None] = []

    async def search_records(
        self,
        table_id: str,
        *,
        page_size: int,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(page_token)
        if page_token is None:
            return {
                "items": [{"record_id": "rec1"}],
                "has_more": True,
                "page_token": "next",
            }
        return {
            "items": [{"record_id": "rec2"}],
            "has_more": False,
            "page_token": None,
        }


@pytest.mark.asyncio
async def test_read_all_records_reads_all_pages() -> None:
    service = WarehouseService.__new__(WarehouseService)
    client = FakeRecordClient()

    records = await service._read_all_records(client, "tbl1")  # type: ignore[arg-type]

    assert [record["record_id"] for record in records] == ["rec1", "rec2"]
    assert client.calls == [None, "next"]


class FakeSession:
    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


class FakeRepo:
    def __init__(self) -> None:
        self.session = FakeSession()


@pytest.mark.asyncio
async def test_set_feishu_tables_enabled_updates_unique_tables_without_sync() -> None:
    service = WarehouseService.__new__(WarehouseService)
    table_a_id = uuid4()
    table_b_id = uuid4()
    tables = {
        table_a_id: WarehouseFeishuTable(id=table_a_id, name="A", is_enabled=False),
        table_b_id: WarehouseFeishuTable(id=table_b_id, name="B", is_enabled=False),
    }
    service.repo = FakeRepo()

    async def fake_get_table(table_pk):
        return tables[table_pk]

    service._get_table_by_id_or_raise = fake_get_table  # type: ignore[method-assign]

    updated = await service.set_feishu_tables_enabled(
        [table_a_id, table_a_id, table_b_id],
        True,
    )

    assert updated == [tables[table_a_id], tables[table_b_id]]
    assert tables[table_a_id].is_enabled is True
    assert tables[table_a_id].sync_status == "pending"
    assert tables[table_b_id].is_enabled is True
    assert tables[table_b_id].sync_status == "pending"
    assert service.repo.session.commits == 1


@pytest.mark.asyncio
async def test_sync_feishu_table_marks_failed_when_sync_timeout(monkeypatch) -> None:
    service = WarehouseService.__new__(WarehouseService)
    table_id = uuid4()
    table = WarehouseFeishuTable(
        id=table_id,
        business_domain="hardware",
        app_token="base",
        table_id="tbl",
        name="五金",
        is_enabled=True,
    )
    config = WarehouseFeishuConfig(
        config_name="仓储飞书配置",
        app_id="cli_123",
        encrypted_app_secret="encrypted",
        hardware_app_token="base",
        is_active=True,
    )
    service.repo = FakeRepo()

    async def fake_get_table(table_pk):
        assert table_pk == table_id
        return table

    async def slow_snapshot(_config, _table):
        await asyncio.sleep(0.05)

    service._get_table_by_id_or_raise = fake_get_table  # type: ignore[method-assign]
    service._sync_feishu_table_snapshot = slow_snapshot  # type: ignore[method-assign]
    monkeypatch.setattr(
        warehouse_service,
        "WAREHOUSE_FEISHU_TABLE_SYNC_TIMEOUT_SECONDS",
        0.01,
    )

    with pytest.raises(AppException):
        await service._sync_feishu_table(config, table)

    assert table.sync_status == "failed"
    assert table.sync_error == "同步超过 0.01 秒未完成，已自动标记失败"
    assert service.repo.session.commits == 2
    assert service.repo.session.rollbacks == 1
