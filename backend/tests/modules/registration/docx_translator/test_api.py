# mypy: ignore-errors
"""文档翻译 —— API 契约测试。

覆盖：
- 提交任务 / 查询状态 / 批量状态的响应信封与字段
- 列表端点的分页必须落在信封 `meta`（而不是 data 里）
- `status` / `mine` 查询参数真正下传
- 删除任务的权限二次判定（无 delete 权限时只能删自己的）
- 术语软删后可重建同名词条（部分唯一索引回归）
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.registration.docx_translator import api as docx_api
from app.modules.registration.docx_translator.models import DocxTranslationTask, DocxTranslationTerm
from app.modules.registration.docx_translator.schemas import DocxTranslationJobState
from app.platform.permission.service.authorization import PermissionContext

BASE = "/api/v1/registration/docx-translator"
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class _StubRegistry:
    """替代真实 registry：不跑翻译、不落 background_jobs。"""

    def __init__(self) -> None:
        self.started: list[tuple[str, int]] = []
        self.state_value = DocxTranslationJobState(job_id="job-1", status="running", files_total=1)

    async def start(self, name: str, files_total: int, runner) -> str:  # type: ignore[no-untyped-def]
        self.started.append((name, files_total))
        return "job-1"

    async def state(self, job_id: str) -> DocxTranslationJobState:
        return self.state_value

    async def states(self, job_ids: list[str]) -> list[DocxTranslationJobState]:
        return [self.state_value] if "job-1" in job_ids else []

    async def result(self, job_id: str) -> dict | None:
        return {"files": []}


@pytest.fixture
def stub_registry(monkeypatch: pytest.MonkeyPatch) -> _StubRegistry:
    stub = _StubRegistry()

    async def _limits() -> tuple[int, int, float]:
        return (50, 10, 90.0)

    async def _batch_size(_value: int | None) -> int:
        return 30

    async def _glossary(_db) -> dict[str, str]:  # type: ignore[no-untyped-def]
        return {}

    monkeypatch.setattr(docx_api, "get_registry", lambda: stub)
    monkeypatch.setattr(docx_api, "load_limits", _limits)
    monkeypatch.setattr(docx_api, "resolve_batch_size", _batch_size)
    monkeypatch.setattr(docx_api, "load_glossary", _glossary)
    return stub


def _task(job_ref: str, *, created_by, status: str = "done") -> DocxTranslationTask:
    return DocxTranslationTask(
        job_ref=job_ref,
        status=status,
        source_count=1,
        success_count=1,
        fail_count=0,
        first_source_filename="a.docx",
        source_lang="en",
        target_lang="zh",
        mode="bilingual",
        batch_size=30,
        elapsed_seconds=12,
        source_keys=[{"filename": "a.docx", "object_key": f"k/{job_ref}", "size": 10}],
        created_by=created_by,
    )


async def test_submit_job_returns_job_id(auth_client: AsyncClient, stub_registry: _StubRegistry) -> None:
    resp = await auth_client.post(
        f"{BASE}/jobs",
        files=[("files", ("a.docx", b"fake-docx-bytes", DOCX_MIME))],
        data={"source_lang": "en", "target_lang": "zh", "mode": "bilingual"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["job_id"] == "job-1"
    assert stub_registry.started == [("docx-translation", 1)]


async def test_job_state_and_batch_state(auth_client: AsyncClient, stub_registry: _StubRegistry) -> None:
    single = await auth_client.get(f"{BASE}/jobs/job-1")
    assert single.status_code == 200
    assert single.json()["data"]["status"] == "running"

    batch = await auth_client.get(f"{BASE}/jobs", params=[("ids", "job-1"), ("ids", "unknown")])
    assert batch.status_code == 200
    items = batch.json()["data"]["items"]
    assert [item["job_id"] for item in items] == ["job-1"]


async def test_task_list_pagination_in_envelope_meta(auth_client: AsyncClient, db_session: AsyncSession) -> None:
    user_id = (await auth_client.get("/api/v1/identity/me")).json()["data"]["id"]
    db_session.add_all([_task(f"job-{uuid.uuid4().hex[:8]}", created_by=user_id) for _ in range(3)])
    await db_session.commit()

    resp = await auth_client.get(f"{BASE}/tasks", params={"page": 1, "page_size": 2})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # 分页必须在信封 meta，data 是纯列表
    assert isinstance(body["data"], list)
    assert body["meta"]["page"] == 1
    assert body["meta"]["page_size"] == 2
    assert body["meta"]["total"] >= 3


async def test_task_list_status_and_mine_filters(auth_client: AsyncClient, db_session: AsyncSession) -> None:
    me = (await auth_client.get("/api/v1/identity/me")).json()["data"]["id"]
    db_session.add_all(
        [
            _task(f"job-{uuid.uuid4().hex[:8]}", created_by=me, status="done"),
            # created_by 为空 = 他人/系统创建（外键要求必须是真实用户）
            _task(f"job-{uuid.uuid4().hex[:8]}", created_by=None, status="failed"),
        ]
    )
    await db_session.commit()

    mine = await auth_client.get(f"{BASE}/tasks", params={"mine": "true"})
    assert mine.status_code == 200
    assert {row["created_by_name"] is not None for row in mine.json()["data"]} == {True}
    assert all(row["can_retranslate"] for row in mine.json()["data"])

    failed = await auth_client.get(f"{BASE}/tasks", params={"status": "failed"})
    assert failed.status_code == 200
    assert all(row["status"] == "failed" for row in failed.json()["data"])


async def test_delete_other_users_task_requires_delete_permission(
    auth_client: AsyncClient,
    db_session: AsyncSession,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    task = _task(f"job-{uuid.uuid4().hex[:8]}", created_by=None)
    db_session.add(task)
    await db_session.commit()

    async def _deny(db, user, permission_code):  # type: ignore[no-untyped-def]
        return PermissionContext(user=user, permission_code=permission_code, is_superuser=False)

    async def _false(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr("app.platform.permission.deps.build_permission_context", _deny)
    monkeypatch.setattr(docx_api, "has_permission", _false)

    resp = await auth_client.delete(f"{BASE}/tasks/{task.id}")
    assert resp.status_code == 403
    assert "只能删除自己创建的翻译任务" in resp.json()["message"]


async def test_delete_own_task_soft_deletes(auth_client: AsyncClient, db_session: AsyncSession) -> None:
    me = (await auth_client.get("/api/v1/identity/me")).json()["data"]["id"]
    task = _task(f"job-{uuid.uuid4().hex[:8]}", created_by=me)
    db_session.add(task)
    await db_session.commit()

    resp = await auth_client.delete(f"{BASE}/tasks/{task.id}")
    assert resp.status_code == 200
    await db_session.refresh(task)
    assert task.is_deleted is True


async def test_glossary_list_pagination_in_envelope_meta(auth_client: AsyncClient) -> None:
    resp = await auth_client.get(f"{BASE}/glossary", params={"page": 1, "page_size": 5})
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["data"], list)
    assert set(body["meta"]) == {"page", "page_size", "total"}


async def test_term_can_be_recreated_after_soft_delete(auth_client: AsyncClient, db_session: AsyncSession) -> None:
    """软删同名词条后再建：部分唯一索引只约束未软删行，不应 500。"""
    term_en = f"audit-term-{uuid.uuid4().hex[:8]}"
    payload = {"term_en": term_en, "term_zh": "审计术语", "is_enabled": True}

    created = await auth_client.post(f"{BASE}/glossary", json=payload)
    assert created.status_code == 200, created.text
    term_id = created.json()["data"]["id"]

    deleted = await auth_client.delete(f"{BASE}/glossary/{term_id}")
    assert deleted.status_code == 200

    again = await auth_client.post(f"{BASE}/glossary", json=payload)
    assert again.status_code == 200, again.text

    rows = (
        (
            await db_session.execute(
                select(DocxTranslationTerm).where(DocxTranslationTerm.term_en_lower == term_en.lower())
            )
        )
        .scalars()
        .all()
    )
    # 一行软删留痕 + 一行新建，两者共存正是部分唯一索引生效的证据
    assert len(rows) == 2
    assert sorted(row.is_deleted for row in rows) == [False, True]
