"""研发报告列表 API 契约测试。

只验证 HTTP 层：`project_id` 可选、`limit` 透传与范围校验、`project_name` 随行返回。
service 被替换，不依赖数据库与真实鉴权。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.modules.research import api as research_api
from app.modules.research.api import router as research_router
from app.modules.research.schemas import RdReportResponse
from app.platform.identity.deps import require_current_user
from app.platform.permission.deps import require_current_user as permission_require_current_user
from app.platform.permission.service.authorization import PermissionContext

NOW = datetime.now(UTC)


def _report(project_id: UUID | None = None, project_name: str | None = "阿莫西林工艺优化") -> RdReportResponse:
    return RdReportResponse(
        id=uuid4(),
        project_id=project_id or uuid4(),
        title="研发总结报告",
        report_type="summary",
        version="v1.0",
        status="draft",
        created_at=NOW,
        updated_at=NOW,
        project_name=project_name,
    )


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(research_router, prefix="/api/v1/research")

    user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[require_current_user] = lambda: user
    app.dependency_overrides[permission_require_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()

    async def _fake_context(db, current_user, code):  # noqa: ANN001, ANN202
        return PermissionContext(user=current_user, permission_code=code)

    monkeypatch.setattr("app.platform.permission.deps.build_permission_context", _fake_context)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def test_list_reports_without_project_id_spans_projects(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    async def _get_reports(db, project_id=None, limit=200):  # noqa: ANN001, ANN202
        seen.update({"project_id": project_id, "limit": limit})
        return [_report(project_name="项目甲"), _report(project_name="项目乙")]

    monkeypatch.setattr(research_api.service, "get_reports", _get_reports)

    response = await client.get("/api/v1/research/reports")

    assert response.status_code == 200
    body = response.json()
    assert seen["project_id"] is None
    assert seen["limit"] == 200
    assert [item["project_name"] for item in body["data"]] == ["项目甲", "项目乙"]


async def test_list_reports_with_project_id_passes_filter(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    async def _get_reports(db, project_id=None, limit=200):  # noqa: ANN001, ANN202
        seen.update({"project_id": project_id, "limit": limit})
        return [_report(project_id=project_id)]

    monkeypatch.setattr(research_api.service, "get_reports", _get_reports)

    project_id = uuid4()
    response = await client.get(f"/api/v1/research/reports?project_id={project_id}&limit=20")

    assert response.status_code == 200
    assert seen["project_id"] == project_id
    assert seen["limit"] == 20
    assert response.json()["data"][0]["project_name"] == "阿莫西林工艺优化"


@pytest.mark.parametrize("limit", [0, 501])
async def test_list_reports_rejects_out_of_range_limit(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, limit: int
) -> None:
    async def _get_reports(db, project_id=None, limit=200):  # noqa: ANN001, ANN202
        return []

    monkeypatch.setattr(research_api.service, "get_reports", _get_reports)

    response = await client.get(f"/api/v1/research/reports?limit={limit}")

    assert response.status_code == 422
