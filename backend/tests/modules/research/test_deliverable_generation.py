"""阶段交付文档 → AI 生成研发报告：编排规则与接口契约测试。

生成引擎（Agent 循环、槽位、渲染）已有独立用例；这里只覆盖本次新增的部分：

1. 预填值推导（标题/版本/受控编码）与模板排序推荐规则；
2. 回写钩子的失败隔离（附件没复制成功不能影响任务终态）；
3. HTTP 契约：静态路径不被 ``/{deliverable_id}`` 吃掉、非法 ID 过滤、必填校验。

全部用例不连数据库、不调真实 LLM / 文件存储。
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.research import deliverable_generation
from app.modules.research.api import router as research_router
from app.modules.research.deliverable_generation import (
    _default_doc_code,
    _has_output,
    _next_version,
    _to_template_options,
    deliverable_type_label,
    stage_label,
)
from app.modules.research.models import RdDeliverableTemplate, RdReportGenJob, RdStageDeliverable
from app.modules.research.schemas import (
    RdDeliverableTemplateOption,
    RdStageDeliverableGenerateResult,
    RdStageDeliverableGenerationOptions,
    RdStageDeliverableGenerationStatus,
    RdStageDeliverableReportLink,
)
from app.platform.identity.deps import require_current_user
from app.platform.permission.service.authorization import PermissionContext

# ===== 预填值推导 =====


def test_next_version_increments_minor() -> None:
    assert _next_version(None) == "v1.0"
    assert _next_version("v1.0") == "v1.1"
    assert _next_version("V2.9") == "v2.10"


def test_next_version_keeps_unrecognized_text() -> None:
    """认不出的历史版本值不能丢用户原文，只追加后缀。"""
    assert _next_version("草稿版") == "草稿版-v2"


def test_default_doc_code_encodes_stage_and_type_index() -> None:
    assert _default_doc_code("initiation", "literature_review") == "RD-01-01"
    assert _default_doc_code("initiation", "development_plan") == "RD-01-02"
    assert _default_doc_code("pilot", "supplier_development") == "RD-04-03"


def test_has_output_requires_attachment() -> None:
    """点过生成但还没出稿（status=in_progress）不算出过稿，再生成要复用同一条。"""
    assert _has_output(None) is False
    assert _has_output(cast(RdStageDeliverable, SimpleNamespace(file_name=None, status="in_progress"))) is False
    assert (
        _has_output(cast(RdStageDeliverable, SimpleNamespace(file_name="研发总方案.docx", status="in_progress")))
        is True
    )


def test_labels_fall_back_without_leaking_keys() -> None:
    assert stage_label("initiation") == "立项"
    assert stage_label("unknown_stage") == "unknown_stage"
    assert deliverable_type_label("development_plan") == "研发总方案"
    assert deliverable_type_label("not_a_type") == "其他类型"


# ===== 模板匹配与推荐 =====


def _template(
    name: str,
    deliverable_type: str,
    *,
    stage: str = "initiation",
    has_file: bool = True,
) -> SimpleNamespace:
    file_name = f"{name}.docx" if has_file else None
    return SimpleNamespace(
        id=uuid4(),
        name=name,
        deliverable_type=deliverable_type,
        stage=stage,
        file_name=file_name,
        file_object_key=f"research/templates/{name}.docx" if has_file else None,
    )


def test_template_options_put_exact_match_with_file_first() -> None:
    exact_without_file = _template("研发总方案-未上传", "development_plan", has_file=False)
    exact_with_file = _template("研发总方案-已上传", "development_plan")
    other_type = _template("技术调研报告", "literature_review")

    options, recommended_id = _to_template_options(
        cast(list[RdDeliverableTemplate], [other_type, exact_without_file, exact_with_file]),
        {},
        "development_plan",
    )

    assert options[0].id == exact_with_file.id
    assert options[0].is_exact_match is True
    assert options[0].is_recommended is True
    assert options[0].has_file is True
    # 缺母本的精确匹配排在「有母本但类型不同」的候选之前：类型对更重要
    assert options[1].id == exact_without_file.id
    assert options[2].id == other_type.id
    assert sum(1 for item in options if item.is_recommended) == 1
    assert recommended_id == exact_with_file.id


def test_template_options_prefer_newer_version() -> None:
    older = _template("研发总方案-旧", "development_plan")
    newer = _template("研发总方案-新", "development_plan")

    options, recommended_id = _to_template_options(
        cast(list[RdDeliverableTemplate], [older, newer]),
        {older.id: 1, newer.id: 3},
        "development_plan",
    )

    assert [item.id for item in options] == [newer.id, older.id]
    assert options[1].version_no == 1
    assert recommended_id == newer.id


def test_template_options_without_file_have_no_recommendation() -> None:
    """所有候选都缺母本时不瞎推荐，让上层给出「去上传」的提示。"""
    only = _template("研发总方案", "development_plan", has_file=False)

    options, recommended_id = _to_template_options(cast(list[RdDeliverableTemplate], [only]), {}, "development_plan")

    assert recommended_id is None
    assert options[0].has_file is False
    assert options[0].is_recommended is False


def test_template_options_do_not_recommend_other_type() -> None:
    """类型不匹配的降级候选只展示，绝不替用户选中，否则会拿错母本出稿。"""
    fallback = _template("技术调研报告", "literature_review")

    options, recommended_id = _to_template_options(
        cast(list[RdDeliverableTemplate], [fallback]), {}, "development_plan"
    )

    assert recommended_id is None
    assert options[0].is_exact_match is False
    assert options[0].is_recommended is False


# ===== 回写钩子：失败隔离 =====


class _StubResult:
    def __init__(self, value: Any) -> None:
        self._value = value

    def scalars(self) -> Any:
        return SimpleNamespace(first=lambda: self._value)


class _RecordingSession:
    """记录查询/落库次数；execute 默认返回给定的交付文档。"""

    def __init__(self, value: Any = None, *, explode: bool = False) -> None:
        self.value = value
        self.explode = explode
        self.calls = 0
        self.flushes = 0

    async def execute(self, *args: Any, **kwargs: Any) -> Any:
        self.calls += 1
        if self.explode:
            raise RuntimeError("database is down")
        return _StubResult(self.value)

    async def flush(self) -> None:
        self.flushes += 1


def _job(status: str, *, object_key: str | None) -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        status=status,
        document_object_key=object_key,
        document_file_name="研发总方案.docx",
    )


def _deliverable() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        title="研发总方案",
        status="in_progress",
        file_name=None,
        file_size=None,
        file_url=None,
    )


async def test_sync_job_result_ignores_unfinished_job() -> None:
    session = _RecordingSession()

    await deliverable_generation.sync_job_result(
        cast(AsyncSession, session), cast(RdReportGenJob, _job("running", object_key="a.docx"))
    )

    assert session.calls == 0


async def test_sync_job_result_ignores_job_without_document() -> None:
    session = _RecordingSession()

    await deliverable_generation.sync_job_result(
        cast(AsyncSession, session), cast(RdReportGenJob, _job("completed", object_key=None))
    )

    assert session.calls == 0


async def test_sync_job_result_swallows_artifact_copy_failures(
    caplog: pytest.LogCaptureFixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """拷文件失败只记日志：报告已经生成好了，不能因为归档失败把任务判失败。"""
    session = _RecordingSession(_deliverable())

    monkeypatch.setattr(
        "app.modules.research.deliverable_generation.artifact_store.load_bytes", lambda key: b"docx-bytes"
    )

    def _boom(*args: Any, **kwargs: Any) -> int:
        raise OSError("disk full")

    monkeypatch.setattr("app.modules.research.deliverable_generation.deliverable_files.save_deliverable_bytes", _boom)

    with caplog.at_level(logging.ERROR):
        await deliverable_generation.sync_job_result(
            cast(AsyncSession, session),
            cast(RdReportGenJob, _job("completed", object_key="research/reports/x.docx")),
        )

    assert session.calls == 1
    assert session.flushes == 0
    assert "stage deliverable artifact copy failed" in caplog.text


async def test_sync_job_result_lets_database_errors_escape() -> None:
    """数据库异常不吞：吞了会让 session 停在失效事务上，调用方 commit 依旧会炸。"""
    session = _RecordingSession(explode=True)

    with pytest.raises(RuntimeError, match="database is down"):
        await deliverable_generation.sync_job_result(
            cast(AsyncSession, session),
            cast(RdReportGenJob, _job("completed", object_key="research/reports/x.docx")),
        )


# ===== HTTP 契约 =====


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(research_router, prefix="/api/v1/research")

    user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[require_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()

    async def _fake_context(db: Any, current_user: Any, code: str) -> PermissionContext:
        return PermissionContext(user=current_user, permission_code=code)

    monkeypatch.setattr("app.platform.permission.deps.build_permission_context", _fake_context)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


def _options(project_id: UUID, template_id: UUID) -> RdStageDeliverableGenerationOptions:
    return RdStageDeliverableGenerationOptions(
        project_id=project_id,
        project_name="阿莫西林",
        api_name="Amoxicillin",
        stage="initiation",
        stage_label="立项",
        deliverable_type="development_plan",
        deliverable_type_label="研发总方案",
        default_title="阿莫西林 - 立项 - 研发总方案",
        default_version="v1.0",
        default_doc_code="RD-01-02",
        templates=[
            RdDeliverableTemplateOption(
                id=template_id,
                name="研发总方案模板",
                deliverable_type="development_plan",
                stage="initiation",
                version_no=1,
                file_name="plan.docx",
                has_file=True,
                is_exact_match=True,
                is_recommended=True,
            )
        ],
        recommended_template_id=template_id,
    )


async def test_generation_options_route_not_shadowed_by_uuid_path(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``generation/options`` 必须命中静态路由，不能被 ``/{deliverable_id}`` 当 UUID 解析成 422。"""
    pid = uuid4()
    template_id = uuid4()
    seen: dict[str, object] = {}

    async def _build_options(
        db: Any,
        *,
        project_id: UUID,
        stage: str,
        deliverable_type: str,
        deliverable_id: UUID | None = None,
    ) -> RdStageDeliverableGenerationOptions:
        seen.update({"project_id": project_id, "stage": stage, "type": deliverable_type, "id": deliverable_id})
        return _options(project_id, template_id)

    monkeypatch.setattr(deliverable_generation, "build_options", _build_options)

    response = await client.get(
        "/api/v1/research/rd-stage-deliverables/generation/options",
        params={"project_id": str(pid), "stage": "initiation", "deliverable_type": "development_plan"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["recommended_template_id"] == str(template_id)
    assert body["data"]["default_version"] == "v1.0"
    assert seen["project_id"] == pid
    assert seen["stage"] == "initiation"
    assert seen["id"] is None


async def test_generation_options_requires_three_locators(client: AsyncClient) -> None:
    response = await client.get("/api/v1/research/rd-stage-deliverables/generation/options")

    assert response.status_code == 422


async def test_generate_endpoint_returns_job_and_hint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    deliverable_id, report_id, job_id = uuid4(), uuid4(), uuid4()
    seen: dict[str, object] = {}

    async def _generate(db: Any, payload: Any, user_id: UUID | None) -> RdStageDeliverableGenerateResult:
        seen["payload"] = payload
        seen["user_id"] = user_id
        return RdStageDeliverableGenerateResult(
            deliverable_id=deliverable_id,
            report_id=report_id,
            job_id=job_id,
            job_status="queued",
            reused=False,
        )

    monkeypatch.setattr(deliverable_generation, "generate", _generate)

    response = await client.post(
        "/api/v1/research/rd-stage-deliverables/generate",
        json={"project_id": str(uuid4()), "stage": "initiation", "deliverable_type": "development_plan"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["job_id"] == str(job_id)
    assert body["data"]["deliverable_id"] == str(deliverable_id)
    assert body["data"]["reused"] is False
    assert "自动归档" in body["message"]
    assert seen["payload"] is not None


async def test_generate_endpoint_rejects_missing_stage(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/research/rd-stage-deliverables/generate",
        json={"project_id": str(uuid4()), "deliverable_type": "development_plan"},
    )

    assert response.status_code == 422


async def test_generation_status_endpoint(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    deliverable_id = uuid4()
    seen: dict[str, object] = {}

    async def _status(db: Any, target: UUID) -> RdStageDeliverableGenerationStatus:
        seen["deliverable_id"] = target
        return RdStageDeliverableGenerationStatus(
            deliverable_id=target,
            status="running",
            progress=42,
            current_step="抽取事实",
            slot_total=10,
            slot_filled=6,
            slot_gap=4,
        )

    monkeypatch.setattr(deliverable_generation, "get_status", _status)

    response = await client.get(f"/api/v1/research/rd-stage-deliverables/{deliverable_id}/generation")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["progress"] == 42
    assert body["data"]["slot_gap"] == 4
    assert seen["deliverable_id"] == deliverable_id


async def test_report_links_filters_invalid_ids(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """前端会一次性传整页报告 ID，其中混入脏值时只跳过脏值，不整条请求失败。"""
    valid = uuid4()
    seen: dict[str, object] = {}

    async def _links(db: Any, ids: list[UUID]) -> list[RdStageDeliverableReportLink]:
        seen["ids"] = ids
        return [
            RdStageDeliverableReportLink(
                report_id=valid,
                deliverable_id=uuid4(),
                project_id=uuid4(),
                stage="initiation",
                stage_label="立项",
                deliverable_type="development_plan",
                deliverable_type_label="研发总方案",
                version="v1.0",
            )
        ]

    monkeypatch.setattr(deliverable_generation, "list_report_links", _links)

    response = await client.get(
        "/api/v1/research/rd-stage-deliverables/report-links",
        params={"report_ids": f"{valid},not-a-uuid"},
    )

    assert response.status_code == 200
    assert seen["ids"] == [valid]
    assert response.json()["data"][0]["report_id"] == str(valid)
