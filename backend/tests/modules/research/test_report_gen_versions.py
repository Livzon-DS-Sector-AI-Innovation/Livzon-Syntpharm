"""报告成品版本 API 契约测试。

覆盖「AI 初稿 → 人工改稿」闭环的只读 HTTP 面：版本列表与版本下载。
与 test_report_gen_api.py 一致，只验路由与响应信封，versions 的业务实现被替换，
不依赖数据库与对象存储。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.modules.research.report_gen import versions as versions_module
from app.modules.research.report_gen.api import router as report_gen_router
from app.modules.research.report_gen.schemas import (
    ReportGenDocumentVersionData,
    ReportGenDocumentVersionListData,
)
from app.platform.identity.deps import require_current_user
from app.platform.permission.deps import require_current_user as permission_require_current_user
from app.platform.permission.service.authorization import PermissionContext

NOW = datetime.now(UTC)


def _version(
    job_id: UUID | None = None,
    *,
    version_no: int = 1,
    kind: str = "ai_draft",
    is_current: bool = True,
) -> ReportGenDocumentVersionData:
    return ReportGenDocumentVersionData(
        id=uuid4(),
        job_id=job_id or uuid4(),
        version_no=version_no,
        kind=kind,
        file_name="化合物A研发总结报告.docx",
        file_size=20480,
        note=None,
        is_current=is_current,
        created_at=NOW,
    )


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(report_gen_router, prefix="/api/v1/research/report-gen")

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


async def test_list_versions_returns_timeline(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _list(db, job_id):  # noqa: ANN001, ANN202
        return ReportGenDocumentVersionListData(
            items=[
                _version(job_id, version_no=2, kind="manual_upload"),
                _version(job_id, version_no=1, kind="ai_draft", is_current=False),
            ],
            total=2,
        )

    monkeypatch.setattr(versions_module, "list_versions", _list)

    response = await client.get(f"/api/v1/research/report-gen/jobs/{uuid4()}/versions")

    assert response.status_code == 200
    items = response.json()["data"]["items"]
    assert [item["kind"] for item in items] == ["manual_upload", "ai_draft"]
    assert items[1]["is_current"] is False


async def test_version_document_download_sets_rfc5987_filename(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _payload(db, version_id):  # noqa: ANN001, ANN202
        return (
            "化合物A研发总结报告-人工改稿.docx",
            b"PK-version-bytes",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    monkeypatch.setattr(versions_module, "version_document_payload", _payload)

    response = await client.get(f"/api/v1/research/report-gen/versions/{uuid4()}/document")

    assert response.status_code == 200
    assert response.content == b"PK-version-bytes"
    disposition = response.headers["content-disposition"]
    assert "attachment;" in disposition
    assert "filename*=UTF-8''" in disposition
