# mypy: ignore-errors
"""D-17 / D-26 回归护栏：前端调用的路径必须解析到后端真实路由。

两条缺陷都是路径写错导致的**必然** 404，静态类型检查发现不了（模板串里的路径是运行时
字符串），所以这里同时断言「正确路径可用」与「错误路径不存在」——只断言前者会在有人把
路径改回去、而测试数据恰好也能走通时漏掉回归。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.modules.energy.models import EnergyCollectLog

DETAIL_PATH = "/api/v1/energy/collect/logs"
BROKEN_DETAIL_PATH = "/api/v1/energy/collect-logs"
FEISHU_IMPORT_PATH = "/api/v1/energy/monthly/import/feishu"
BROKEN_FEISHU_IMPORT_PATH = "/api/v1/energy/import/feishu"


async def _insert_log(db_session) -> str:
    log = EnergyCollectLog(
        platform_code=f"zhiheng-{uuid4().hex[:8]}",
        collect_time=datetime(2001, 5, 1, tzinfo=UTC),
        status="success",
        device_count=0,
        success_count=0,
        error_message=None,
    )
    db_session.add(log)
    await db_session.flush()
    return str(log.id)


async def test_collect_log_detail_uses_real_backend_path(auth_client, db_session):
    log_id = await _insert_log(db_session)

    response = await auth_client.get(f"{DETAIL_PATH}/{log_id}/detail")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["id"] == log_id
    # 无设备数据时明细为空但响应结构完整（前端抽屉按 devices 渲染表格）
    assert data["devices"] == []


async def test_old_collect_log_path_is_not_routed(auth_client, db_session):
    log_id = await _insert_log(db_session)

    assert (await auth_client.get(f"{BROKEN_DETAIL_PATH}/{log_id}")).status_code == 404


@dataclass
class _FakeResult:
    workshops_created: int = 1
    workshops_existing: int = 2
    records_created: int = 3
    records_skipped: int = 4
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.errors = self.errors or []


async def test_feishu_import_uses_real_backend_path(auth_client):
    # 飞书是外部依赖，必须 mock；dry_run 也会真实读电子表格
    with patch("app.modules.energy.feishu_import.FeishuEnergyImporter") as importer_cls:
        importer_cls.return_value.import_from_spreadsheet = AsyncMock(return_value=_FakeResult())

        response = await auth_client.post(
            FEISHU_IMPORT_PATH,
            json={
                # 与 FeishuImportModal.handleDryRun 发的一致
                "spreadsheet_token": "fake-token",
                "sheet_id": None,
                "source": "feishu_bitable",
                "dry_run": True,
            },
        )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["workshops_created"] == 1
    assert data["records_skipped"] == 4
    assert data["errors"] == []


async def test_old_feishu_import_path_is_not_routed(auth_client):
    with patch("app.modules.energy.feishu_import.FeishuEnergyImporter"):
        response = await auth_client.post(
            BROKEN_FEISHU_IMPORT_PATH,
            json={"spreadsheet_token": "fake-token", "dry_run": True},
        )

    assert response.status_code == 404
