"""报告成品版本 API 契约测试。

覆盖「AI 初稿 → 人工改稿」闭环的 HTTP 面：重渲染、版本列表、上传改稿、
版本下载与「设为当前」。与 test_report_gen_api.py 一致，只验路由与响应信封，
versions 的业务实现被替换，不依赖数据库与对象存储。
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
    ReportGenRenderData,
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


def _render_data(job_id: UUID, *, synced: bool = True) -> ReportGenRenderData:
    return ReportGenRenderData(
        version=_version(job_id, version_no=2, kind="manual_render", is_current=True),
        filled=12,
        gaps=1,
        unresolved=[],
        synced_deliverable=synced,
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


async def test_render_returns_new_version(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    async def _render(db, job_id, user_id):  # noqa: ANN001, ANN202
        seen["job_id"] = job_id
        return _render_data(job_id)

    monkeypatch.setattr(versions_module, "render_from_slots", _render)

    job_id = uuid4()
    response = await client.post(f"/api/v1/research/report-gen/jobs/{job_id}/render")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["version"]["kind"] == "manual_render"
    assert body["data"]["filled"] == 12
    assert body["message"] == "已按当前内容重新生成 Word"
    assert seen["job_id"] == job_id


async def test_render_warns_when_deliverable_not_synced(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _render(db, job_id, user_id):  # noqa: ANN001, ANN202
        return _render_data(job_id, synced=False)

    monkeypatch.setattr(versions_module, "render_from_slots", _render)

    response = await client.post(f"/api/v1/research/report-gen/jobs/{uuid4()}/render")

    assert response.status_code == 200
    assert "未同步" in response.json()["message"]


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


async def test_upload_version_passes_file(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    async def _upload(db, job_id, upload, user_id):  # noqa: ANN001, ANN202
        seen["content"] = await upload.read()
        seen["file_name"] = upload.filename
        return _render_data(job_id)

    monkeypatch.setattr(versions_module, "upload_version", _upload)

    response = await client.post(
        f"/api/v1/research/report-gen/jobs/{uuid4()}/versions/upload",
        files={"file": ("改稿.docx", b"PK-modified", "application/octet-stream")},
    )

    assert response.status_code == 200
    assert seen["content"] == b"PK-modified"
    assert seen["file_name"] == "改稿.docx"
    assert response.json()["message"] == "已上传并设为当前版本"


async def test_activate_version(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    version_id = uuid4()
    seen: dict[str, object] = {}

    async def _activate(db, target_id, user_id):  # noqa: ANN001, ANN202
        seen["version_id"] = target_id
        return _render_data(uuid4())

    monkeypatch.setattr(versions_module, "activate_version", _activate)

    response = await client.post(f"/api/v1/research/report-gen/versions/{version_id}/activate")

    assert response.status_code == 200
    assert seen["version_id"] == version_id
    assert response.json()["message"] == "已切换到该版本"


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