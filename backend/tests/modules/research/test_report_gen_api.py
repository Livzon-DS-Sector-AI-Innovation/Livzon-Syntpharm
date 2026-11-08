"""AI 报告生成 API 契约测试。

只验证 HTTP 层：路由挂载、请求参数透传、响应信封与文件下载头。
service 与权限判定都被替换，不依赖数据库、不依赖真实 LLM。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.modules.research.report_gen import service as service_module
from app.modules.research.report_gen.api import router as report_gen_router
from app.modules.research.report_gen.schemas import (
    ReportGenJobData,
    ReportGenJobListData,
    ReportGenSlotData,
    ReportGenSlotListData,
    ReportGenStepData,
    ReportGenStepListData,
)
from app.platform.identity.deps import require_current_user
from app.platform.permission.deps import require_current_user as permission_require_current_user
from app.platform.permission.service.authorization import PermissionContext

NOW = datetime.now(UTC)


def _job(job_id: UUID | None = None, **overrides: object) -> ReportGenJobData:
    payload: dict[str, object] = {
        "id": job_id or uuid4(),
        "report_id": uuid4(),
        "project_id": uuid4(),
        "report_title": "化合物A研发总结报告",
        "template_file_name": "研发总结模板.docx",
        "status": "running",
        "progress": 40,
        "current_step": "检索知识库：工艺参数",
        "slot_total": 12,
        "slot_filled": 5,
        "slot_gap": 2,
        "rounds": 3,
        "has_document": False,
        "created_at": NOW,
        "doc_code": "RD-2026-001",
        "drug_name": "化合物A",
    }
    payload.update(overrides)
    return ReportGenJobData.model_validate(payload)


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


async def test_create_job_returns_201_with_envelope(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    created: list[dict[str, object]] = []

    async def _create_job(db, payload, user_id):  # noqa: ANN001, ANN202
        created.append(payload.model_dump())
        return _job(report_id=payload.report_id, project_id=payload.project_id)

    monkeypatch.setattr(service_module, "create_job", _create_job)

    report_id, project_id = uuid4(), uuid4()
    response = await client.post(
        "/api/v1/research/report-gen/jobs",
        json={
            "report_id": str(report_id),
            "project_id": str(project_id),
            # 母本是必填项：不传会先被 422 拦住，测不到透传
            "deliverable_template_id": str(uuid4()),
            "doc_code": "RD-2026-001",
            "drug_name": "化合物A",
            "supplement_text": "补充说明",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["message"] == "已提交生成任务"
    assert body["data"]["status"] == "running"
    assert created and created[0]["report_id"] == report_id


async def test_list_jobs_passes_filters(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    async def _list_jobs(db, *, project_id=None, report_id=None, limit=100):  # noqa: ANN001, ANN202
        seen.update({"project_id": project_id, "report_id": report_id, "limit": limit})
        return ReportGenJobListData(items=[_job()], active_count=1)

    monkeypatch.setattr(service_module, "list_jobs", _list_jobs)

    project_id = uuid4()
    response = await client.get(f"/api/v1/research/report-gen/jobs?project_id={project_id}&limit=10")

    assert response.status_code == 200
    assert seen["project_id"] == project_id
    assert seen["limit"] == 10
    assert response.json()["data"]["active_count"] == 1


async def test_steps_support_after_seq(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    seen: dict[str, object] = {}

    async def _list_steps(db, job_id, *, after_seq=0, limit=200):  # noqa: ANN001, ANN202
        seen.update({"job_id": job_id, "after_seq": after_seq, "limit": limit})
        return ReportGenStepListData(
            items=[
                ReportGenStepData(
                    id=uuid4(),
                    seq=9,
                    kind="tool_call",
                    title="检索知识库",
                    tool_name="search_knowledge_base",
                    status="ok",
                    duration_ms=1200,
                    created_at=NOW,
                )
            ],
            last_seq=9,
        )

    monkeypatch.setattr(service_module, "list_steps", _list_steps)

    job_id = uuid4()
    response = await client.get(f"/api/v1/research/report-gen/jobs/{job_id}/steps?after_seq=8")

    assert response.status_code == 200
    assert seen["after_seq"] == 8
    assert response.json()["data"]["last_seq"] == 9
    assert response.json()["data"]["items"][0]["tool_name"] == "search_knowledge_base"


async def test_list_slots_and_update_slot(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _list_slots(db, job_id):  # noqa: ANN001, ANN202
        return ReportGenSlotListData(
            items=[ReportGenSlotData(slot_key="drug_name", slot_label="品种名称", state="filled", value="化合物A")],
            total=1,
            filled=1,
            gaps=0,
        )

    async def _update_slot(db, job_id, slot_key, payload, user_id):  # noqa: ANN001, ANN202
        return ReportGenSlotData(slot_key=slot_key, slot_label="品种名称", state="filled", value=payload.value)

    monkeypatch.setattr(service_module, "list_slots", _list_slots)
    monkeypatch.setattr(service_module, "update_slot", _update_slot)

    job_id = uuid4()
    slots = await client.get(f"/api/v1/research/report-gen/jobs/{job_id}/slots")
    assert slots.status_code == 200
    assert slots.json()["data"]["filled"] == 1

    updated = await client.put(
        f"/api/v1/research/report-gen/jobs/{job_id}/slots/drug_name",
        json={"value": "化合物B"},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["value"] == "化合物B"


async def test_cancel_job(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _cancel(db, job_id, user_id):  # noqa: ANN001, ANN202
        return _job(job_id=job_id, status="cancelled", progress=40)

    monkeypatch.setattr(service_module, "cancel_job", _cancel)

    job_id = uuid4()
    response = await client.post(f"/api/v1/research/report-gen/jobs/{job_id}/cancel")

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "cancelled"


async def test_document_download_sets_rfc5987_filename(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _payload(db, job_id):  # noqa: ANN001, ANN202
        return (
            "化合物A研发总结报告.docx",
            b"PK-docx-bytes",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    monkeypatch.setattr(service_module, "document_payload", _payload)

    response = await client.get(f"/api/v1/research/report-gen/jobs/{uuid4()}/document")

    assert response.status_code == 200
    assert response.content == b"PK-docx-bytes"
    disposition = response.headers["content-disposition"]
    assert "attachment;" in disposition
    assert "filename*=UTF-8''" in disposition


async def test_comparison_download_returns_markdown(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    async def _payload(db, job_id):  # noqa: ANN001, ANN202
        return ("对照表.md", b"# \xe6\xa7\xbd\xe4\xbd\x8d\xe5\xaf\xb9\xe7\x85\xa7\xe8\xa1\xa8\n", "text/markdown")

    monkeypatch.setattr(service_module, "comparison_payload", _payload)

    response = await client.get(f"/api/v1/research/report-gen/jobs/{uuid4()}/comparison")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/markdown")
