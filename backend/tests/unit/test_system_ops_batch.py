# mypy: ignore-errors
"""定时任务 / API 接口开关的批量操作。

产品口径（2026-10-22）：
- 定时任务逐条运行时启停，找不到的名字记入失败；
- API 开关禁用时保护名单内接口一律拒绝，其余照常；启用不受保护名单限制。
"""

import uuid
from typing import Any

import pytest

from app.platform.permission.public_api import PermissionContext
from app.platform.system import ops_api
from app.platform.system.ops_api import system_api_routes_batch_switch, system_scheduled_tasks_batch_toggle
from app.platform.system.ops_schemas import ApiSwitchBatchItem, ApiSwitchBatchRequest, TaskBatchToggleRequest


def _ctx() -> PermissionContext:
    operator = type("U", (), {})()
    operator.id = uuid.uuid4()
    return PermissionContext(user=operator, permission_code="platform:ops:manage", is_superuser=True)


# ── 定时任务 ──────────────────────────────────────────────────────────


async def test_task_batch_toggle_reports_unknown_names(monkeypatch: pytest.MonkeyPatch) -> None:
    known = {"energy.daily_sync", "identity.sync_members"}

    def fake_set(name: str, enabled: bool) -> bool:
        return name in known

    monkeypatch.setattr(ops_api.ops_service, "set_task_enabled", fake_set)

    resp = await system_scheduled_tasks_batch_toggle(
        TaskBatchToggleRequest(names=["energy.daily_sync", "not.exist"], enabled=False),
        ctx=_ctx(),
    )

    assert resp.data.succeeded == ["energy.daily_sync"]
    assert resp.data.failed[0].key == "not.exist"
    assert resp.data.failed[0].reason == "任务不存在或不可切换"


# ── API 开关 ──────────────────────────────────────────────────────────


async def test_api_batch_switch_rejects_protected_when_disabling(monkeypatch: pytest.MonkeyPatch) -> None:
    switched: list[tuple[str, str, bool]] = []

    async def fake_set_switch(method: str, route: str, enabled: bool, reason: Any, actor_id: Any) -> None:
        switched.append((method, route, enabled))

    monkeypatch.setattr(
        ops_api.api_switch_service,
        "is_protected_route",
        lambda route: route.startswith("/api/v1/system"),
    )
    monkeypatch.setattr(ops_api.api_switch_service, "set_switch", fake_set_switch)

    resp = await system_api_routes_batch_switch(
        ApiSwitchBatchRequest(
            items=[
                ApiSwitchBatchItem(method="GET", route="/api/v1/system/health"),
                ApiSwitchBatchItem(method="GET", route="/api/v1/quality/inspections"),
            ],
            enabled=False,
            reason="维护",
        ),
        ctx=_ctx(),
    )

    assert resp.data.succeeded == ["GET /api/v1/quality/inspections"]
    assert resp.data.failed[0].reason == "保护名单内接口不允许禁用"
    assert switched == [("GET", "/api/v1/quality/inspections", False)]


async def test_api_batch_switch_allows_protected_when_enabling(monkeypatch: pytest.MonkeyPatch) -> None:
    switched: list[tuple[str, str, bool]] = []

    async def fake_set_switch(method: str, route: str, enabled: bool, reason: Any, actor_id: Any) -> None:
        switched.append((method, route, enabled))

    monkeypatch.setattr(ops_api.api_switch_service, "is_protected_route", lambda route: True)
    monkeypatch.setattr(ops_api.api_switch_service, "set_switch", fake_set_switch)

    resp = await system_api_routes_batch_switch(
        ApiSwitchBatchRequest(
            items=[ApiSwitchBatchItem(method="GET", route="/api/v1/system/health")],
            enabled=True,
            reason=None,
        ),
        ctx=_ctx(),
    )

    assert resp.data.succeeded == ["GET /api/v1/system/health"]
    assert resp.data.failed == []
    assert switched == [("GET", "/api/v1/system/health", True)]


async def test_api_batch_switch_deduplicates_and_reports_value_error(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_set_switch(method: str, route: str, enabled: bool, reason: Any, actor_id: Any) -> None:
        raise ValueError("路由不存在")

    monkeypatch.setattr(ops_api.api_switch_service, "is_protected_route", lambda route: False)
    monkeypatch.setattr(ops_api.api_switch_service, "set_switch", fake_set_switch)

    item = ApiSwitchBatchItem(method="get", route="/api/v1/quality/x")
    resp = await system_api_routes_batch_switch(
        ApiSwitchBatchRequest(items=[item, item], enabled=False, reason=None),
        ctx=_ctx(),
    )

    assert resp.data.succeeded == []
    assert len(resp.data.failed) == 1
    assert resp.data.failed[0].reason == "路由不存在"
