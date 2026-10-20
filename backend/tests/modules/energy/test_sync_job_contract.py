# mypy: ignore-errors
"""D-48 契约护栏：异步导入任务的状态必须是**有类型**的响应。

`SyncJobApiResponse.data` 曾经是 `dict[str, Any]`，OpenAPI 只能生成裸 `object`，
前端于是手写了假的返回类型，`result.total_created` 编译期无人拦截 —— 弹窗把
「任务已受理」当「导入成功」渲染就是这么来的。所以这里最重要的断言不是业务值，
而是第 1 条：spec 里 `data` 必须解析到具体模型。
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from app.modules.energy import api as energy_api
from app.modules.energy.job_store import sync_job_store

SUBMIT_ENDPOINTS = [
    ("/api/v1/energy/sync/bitable", None),
    ("/api/v1/energy/sync/bitable/workshops", None),
    ("/api/v1/energy/sync/bitable/monthly", None),
    ("/api/v1/energy/sync/bitable/cross-import", {"month": "2099-01"}),
    ("/api/v1/energy/sync/bitable/daily-import", None),
]

JOB_PATH = "/api/v1/energy/jobs"


def _refs(node: object) -> Iterator[str]:
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield value
            else:
                yield from _refs(value)
    elif isinstance(node, list):
        for item in node:
            yield from _refs(item)


@pytest.fixture
def no_spawn(monkeypatch):
    """拦住后台任务派发：测试里不能真打飞书，未 await 的协程要显式关闭。"""

    def _fake_spawn(coro, **kwargs):
        coro.close()

    monkeypatch.setattr(energy_api, "spawn_task", _fake_spawn)


async def test_job_response_schema_is_typed():
    """`data` 必须解析到 SyncJobStatus，绝不能退回无字段的裸 object。"""
    from app.main import app

    spec = app.openapi()
    schemas = spec["components"]["schemas"]
    data_schema = schemas["SyncJobApiResponse"]["properties"]["data"]

    refs = set(_refs(data_schema))
    assert "#/components/schemas/SyncJobStatus" in refs, f"data 未引用具体模型：{data_schema}"

    status_props = schemas["SyncJobStatus"]["properties"]
    assert status_props["status"]["enum"] == ["running", "done", "failed"]
    assert "#/components/schemas/SyncJobResult" in set(_refs(status_props["result"]))

    result_props = schemas["SyncJobResult"]["properties"]
    for field in ("total_created", "total_updated", "auto_check_alerts", "rollup_warnings"):
        assert field in result_props, f"导入结果缺少 {field}"


@pytest.mark.parametrize("path,body", SUBMIT_ENDPOINTS)
async def test_submit_returns_only_a_job_handle(auth_client, no_spawn, path, body):
    resp = await auth_client.post(path, json=body) if body else await auth_client.post(path)

    assert resp.status_code == 200, resp.text
    data = resp.json()["data"]
    assert data["status"] == "running"
    assert data["job_id"]
    # 受理时还没有任何计数 —— 前端必须轮询才能拿到结果（D-48 的误导点）
    assert data["result"] is None
    assert data["error"] is None


async def test_job_status_running_then_done(auth_client):
    job_id = sync_job_store.create()

    running = (await auth_client.get(f"{JOB_PATH}/{job_id}")).json()["data"]
    assert running["status"] == "running"
    assert running["result"] is None

    sync_job_store.complete(
        job_id,
        {
            "status": "success",
            "table": "2026-10",
            "total_created": 3,
            "total_updated": 6,
            "total_parsed": 117,
            "total_errors": 0,
            "errors": [],
            "rollup_warnings": ["动力运行 与构成项差 2%"],
        },
    )

    done = (await auth_client.get(f"{JOB_PATH}/{job_id}")).json()["data"]
    assert done["status"] == "done"
    assert done["result"]["total_created"] == 3
    assert done["result"]["total_updated"] == 6
    assert done["result"]["rollup_warnings"] == ["动力运行 与构成项差 2%"]


async def test_job_status_drops_unknown_keys(auth_client):
    """导入器会随手加键；契约必须显式声明而不是无限膨胀。"""
    job_id = sync_job_store.create()
    sync_job_store.complete(job_id, {"total_created": 1, "not_in_contract": "x"})

    result = (await auth_client.get(f"{JOB_PATH}/{job_id}")).json()["data"]["result"]

    assert result["total_created"] == 1
    assert "not_in_contract" not in result


async def test_job_status_failed_carries_error(auth_client):
    job_id = sync_job_store.create()
    sync_job_store.fail(job_id, "飞书 token 失效")

    data = (await auth_client.get(f"{JOB_PATH}/{job_id}")).json()["data"]

    assert data["status"] == "failed"
    assert data["error"] == "飞书 token 失效"
    assert data["result"] is None


async def test_unknown_job_is_404(auth_client):
    """进程内 store 重启即丢（D-11），轮询方必须能区分「查不到」与「还没跑完」。"""
    resp = await auth_client.get(f"{JOB_PATH}/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


async def test_import_year_aggregates_month_counts(monkeypatch):
    """D-49：按年导入曾读 `created`/`updated`，而 `import_month` 给的是
    `total_created`/`total_updated` —— 键名不一致让年度计数恒为 0。"""
    from types import SimpleNamespace

    from app.modules.energy import bitable_cross_import as bci

    monkeypatch.setattr(bci, "FeishuClient", lambda *a, **k: SimpleNamespace())
    importer = bci.EnergyBitableCrossImport(app_token="test-token")

    async def fake_tables():
        return [{"name": "2026-08", "table_id": "t8"}, {"name": "2026-09", "table_id": "t9"}]

    async def fake_import_month(db, table_name):
        return {
            "status": "success",
            "table": table_name,
            "total_created": 2,
            "total_updated": 5,
            "total_parsed": 7,
            "errors": [],
            "rollup_warnings": [],
        }

    monkeypatch.setattr(importer, "list_tables", fake_tables)
    monkeypatch.setattr(importer, "import_month", fake_import_month)

    result = await importer.import_year(None, 2026)

    assert result["months_imported"] == 2
    assert result["total_created"] == 4
    assert result["total_updated"] == 10
    assert result["total_errors"] == 0
