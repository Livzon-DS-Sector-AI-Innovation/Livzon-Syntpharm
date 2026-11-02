"""AI 优化改成 job + 轮询后的接口契约。

`AGENTS.md:310` 禁止在 HTTP 请求里跑超过 5 秒的操作，而 LLM 优化常态 5–30 秒，
所以 `POST /ai/optimize` 只入队并返回 202 + job_id，结果由
`GET /ai/optimize/jobs/{id}` 轮询。

## 覆盖范围

- POST 返回 202，信封 `code` 与 HTTP 状态一致，job_id 是可用于轮询的 uuid
- 轮询在 `done` 时透出 `optimized_text`、在 `failed` 时透出 `error`
- 不存在 / 非法 job_id 一律 404，而不是 500 或空 200

worker 不在这里跑：它用独立会话，看不到 fixture 里 `flush` 但未 `commit` 的用户，
理由同 `test_static_data_import_job.py`（worker 路径由 CI 的 e2e 覆盖）。
这里直接写 job 行来断言轮询接口的契约。
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.job_models import JOB_DONE, JOB_FAILED
from app.core.job_repository import JobRepository
from app.modules.quality.qms import deviation_report_api

BASE = "/api/v1/quality/deviation-report"
JOB_KIND = "quality.deviation-ai-optimize"

pytestmark = pytest.mark.usefixtures("db_session")


async def test_optimize_returns_a_job_handle(
    auth_client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """过去这里 200 直出结果，请求要挂二三十秒。"""
    submitted: list[str] = []

    async def _fake_submit(kind: str, _factory: object) -> None:
        submitted.append(kind)

    # 真正的 worker 会去调 LLM 和独立会话，这里只验"请求侧契约"：入队 + 立刻返回
    monkeypatch.setattr(deviation_report_api, "submit_job", _fake_submit)

    response = await auth_client.post(
        f"{BASE}/ai/optimize",
        json={"text": "偏差描述草稿", "optimize_type": "polish"},
    )

    assert response.status_code == 202, response.text
    body = response.json()
    assert body["code"] == 202, "信封 code 必须与 HTTP 状态一致"
    job_id = body["data"]["job_id"]
    # 必须是 poll 路由能解析的 uuid —— 它现在是行主键
    uuid.UUID(job_id)
    assert body["data"]["status"] in {"pending", "running"}
    assert submitted == [JOB_KIND]


async def test_polling_returns_the_optimized_text(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    repo = JobRepository(db_session)
    job_id = await repo.create(JOB_KIND)
    await repo.complete(job_id, {"optimized_text": "润色后的偏差描述"})

    response = await auth_client.get(f"{BASE}/ai/optimize/jobs/{job_id}")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == JOB_DONE
    assert data["optimized_text"] == "润色后的偏差描述"
    assert data["error"] is None


async def test_polling_surfaces_the_failure(
    auth_client: AsyncClient,
    db_session: AsyncSession,
) -> None:
    """后台失败没有调用方可以回报，只能靠 job.error 传给轮询方。"""
    repo = JobRepository(db_session)
    job_id = await repo.create(JOB_KIND)
    await repo.fail(job_id, "provider timeout")

    response = await auth_client.get(f"{BASE}/ai/optimize/jobs/{job_id}")

    data = response.json()["data"]
    assert data["status"] == JOB_FAILED
    assert data["error"] == "provider timeout"
    assert data["optimized_text"] is None


async def test_unknown_job_returns_404(auth_client: AsyncClient) -> None:
    response = await auth_client.get(f"{BASE}/ai/optimize/jobs/{uuid.uuid4()}")
    assert response.status_code == 404, response.text


async def test_malformed_job_id_returns_404(auth_client: AsyncClient) -> None:
    """非 uuid 无法指向任何行，按不存在处理，不能是 500。"""
    response = await auth_client.get(f"{BASE}/ai/optimize/jobs/not-a-uuid")
    assert response.status_code == 404, response.text
