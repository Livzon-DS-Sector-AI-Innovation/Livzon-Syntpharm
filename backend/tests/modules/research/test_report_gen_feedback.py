"""P3 评审意见闭环的单元测试。

不连数据库、不调 LLM：
- 拼接：无意见原样返回、有意见编号成清单、超长截断、原文补充说明在前；
- 生命周期：新任务接手后标 applied 并记 applied_job_id，重新打开清掉该记；
- 校验：槽位级意见必须落在本任务真实存在的槽位上；
- 接口：POST/GET/PATCH 的状态码与响应外壳。
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.core.exceptions import BadRequestException
from app.modules.research.models import RdReportGenExample, RdReportGenFeedback, RdReportGenJob
from app.modules.research.report_gen import service as service_module
from app.modules.research.report_gen.api import router as report_gen_router
from app.modules.research.report_gen.feedback import (
    MAX_FEEDBACK_CHARS,
    mark_applied,
    merge_supplement,
)
from app.modules.research.report_gen.schemas import (
    ReportGenExamplePromoteData,
    ReportGenFeedbackCreateRequest,
    ReportGenFeedbackData,
    ReportGenFeedbackListData,
    ReportGenFeedbackUpdateRequest,
)
from app.platform.identity.deps import require_current_user
from app.platform.permission.deps import require_current_user as permission_require_current_user
from app.platform.permission.service.authorization import PermissionContext

NOW = datetime.now(UTC)


class _Result:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _Result:
        return self

    def all(self) -> list[Any]:
        return list(self._rows)

    def first(self) -> Any:
        return self._rows[0] if self._rows else None


class _Session:
    """够用的假 session：只实现被测代码真正调用到的那几个方法。"""

    def __init__(
        self,
        *,
        job: Any = None,
        slot_keys: list[str] | None = None,
        slot: Any = None,
        feedback: Any = None,
        rows: list[Any] | None = None,
    ) -> None:
        self.job = job
        self.slot_keys = slot_keys or []
        self.slot = slot
        self.feedback = feedback
        self.rows = rows or []
        self.added: list[Any] = []
        self.commits = 0
        self.flushes = 0

    async def get(self, model: Any, _pk: Any) -> Any:
        if model is RdReportGenJob:
            return self.job
        return self.feedback

    async def execute(self, stmt: Any) -> _Result:
        text = str(stmt)
        if "rd_report_gen_slots" in text:
            if self.slot is not None:
                return _Result([self.slot])
            if self.slot_keys:
                return _Result([uuid4() for _ in self.slot_keys])
        return _Result(self.rows)

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, obj: Any) -> None:
        if getattr(obj, "created_at", None) is None:
            obj.created_at = NOW


def _feedback_row(**overrides: Any) -> Any:
    row = SimpleNamespace(
        id=uuid4(),
        job_id=uuid4(),
        report_id=uuid4(),
        slot_key=None,
        content="把结果与讨论写细一点",
        status="open",
        applied_job_id=None,
        created_at=NOW,
        updated_at=NOW,
        is_deleted=False,
        created_by=None,
        updated_by=None,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _job() -> Any:
    return SimpleNamespace(id=uuid4(), report_id=uuid4(), is_deleted=False)


# ---------------------------------------------------------------- 拼接


def test_merge_supplement_without_feedback_keeps_base() -> None:
    assert merge_supplement("  品种名统一用通用名  ", []) == "品种名统一用通用名"
    assert merge_supplement(None, []) == ""


def test_merge_supplement_numbers_items_and_marks_scope() -> None:
    items = [
        _feedback_row(content="结果与讨论写细一点"),
        _feedback_row(slot_key="study_conclusion", content="结论要落到工艺参数"),
    ]

    merged = merge_supplement("品种名统一用通用名", items)

    assert merged.startswith("品种名统一用通用名")
    assert "【上一版评审意见" in merged
    assert "1. [整篇] 结果与讨论写细一点" in merged
    assert "2. [槽位 study_conclusion] 结论要落到工艺参数" in merged


def test_merge_supplement_clips_long_content_and_flattens_newlines() -> None:
    long_text = "问" * (MAX_FEEDBACK_CHARS + 50)

    merged = merge_supplement(None, [_feedback_row(content=f"第一行\n第二行{long_text}")])

    assert "第一行 第二行" in merged
    # 截断按整条 content 算，前缀「第一行 第二行」占掉 6 个字
    assert merged.count("问") == MAX_FEEDBACK_CHARS - len("第一行 第二行")
    assert merged.endswith("…")


async def test_mark_applied_sets_status_and_job() -> None:
    items = [_feedback_row(), _feedback_row()]
    job_id = uuid4()
    session = _Session()

    count = await mark_applied(session, items, job_id)

    assert count == 2
    assert all(item.status == "applied" for item in items)
    assert all(item.applied_job_id == job_id for item in items)
    assert session.flushes == 1


# ---------------------------------------------------------------- service


async def test_create_feedback_rejects_unknown_slot() -> None:
    session = _Session(job=_job(), slot_keys=[])

    with pytest.raises(BadRequestException):
        await service_module.create_feedback(
            session,
            session.job.id,
            ReportGenFeedbackCreateRequest(slot_key="not_exist", content="改一下"),
            None,
        )


async def test_create_feedback_normalizes_content() -> None:
    session = _Session(job=_job(), slot_keys=["study_conclusion"])

    data = await service_module.create_feedback(
        session,
        session.job.id,
        ReportGenFeedbackCreateRequest(slot_key="study_conclusion", content="  结论\n\n要重写  "),
        None,
    )

    assert data.content == "结论 要重写"
    assert data.slot_key == "study_conclusion"
    assert data.status == "open"
    assert session.commits == 1
    assert isinstance(session.added[0], RdReportGenFeedback)


async def test_list_feedback_counts_open_items() -> None:
    rows = [_feedback_row(), _feedback_row(status="applied", applied_job_id=uuid4())]
    session = _Session(job=_job(), rows=rows)

    data = await service_module.list_feedback(session, session.job.id)

    assert data.total == 2
    assert data.open_count == 1
    assert data.items[0].status == "open"


async def test_update_feedback_reopen_clears_applied_job() -> None:
    applied_job_id = uuid4()
    row = _feedback_row(status="applied", applied_job_id=applied_job_id)
    session = _Session(feedback=row)

    data = await service_module.update_feedback(
        session,
        row.id,
        ReportGenFeedbackUpdateRequest(status="open"),
        uuid4(),
    )

    assert data.status == "open"
    assert data.applied_job_id is None
    assert row.applied_job_id is None


# ---------------------------------------------------------------- 沉淀为示例


def _applied_feedback(**overrides: Any) -> Any:
    return _feedback_row(status="applied", applied_job_id=uuid4(), slot_key="study_conclusion", **overrides)


def _promote_session(row: Any, *, slot_value: str | None = "收率 92%，与工艺验证批一致") -> _Session:
    slot = SimpleNamespace(slot_key=row.slot_key, slot_label="研究结论", value=slot_value)
    job = SimpleNamespace(id=row.applied_job_id, deliverable_template_id=uuid4(), is_deleted=False)
    return _Session(job=job, feedback=row, slot=slot, rows=[])


async def test_promote_requires_slot_level_feedback() -> None:
    row = _feedback_row(status="applied", applied_job_id=uuid4())
    session = _Session(feedback=row)

    with pytest.raises(BadRequestException):
        await service_module.promote_feedback(session, row.id, None)


async def test_promote_requires_applied_status() -> None:
    row = _feedback_row(slot_key="study_conclusion")
    session = _Session(feedback=row)

    with pytest.raises(BadRequestException):
        await service_module.promote_feedback(session, row.id, None)


async def test_promote_rejects_blank_slot_value() -> None:
    row = _applied_feedback()
    session = _promote_session(row, slot_value="   ")

    with pytest.raises(BadRequestException):
        await service_module.promote_feedback(session, row.id, None)


async def test_promote_creates_example_from_applied_value() -> None:
    row = _applied_feedback(content="结论要落到收率与批次")
    session = _promote_session(row)

    data = await service_module.promote_feedback(session, row.id, uuid4())

    assert data.slot_key == "study_conclusion"
    assert data.value == "收率 92%，与工艺验证批一致"
    assert data.source == "feedback_promoted"
    assert data.created is True

    example = session.added[0]
    assert isinstance(example, RdReportGenExample)
    assert example.source == "feedback_promoted"
    # 意见原文进 evidence_text：示例库要能回答「为什么这里该这么写」
    assert example.evidence_text == "结论要落到收率与批次"
    assert session.commits == 1


# ---------------------------------------------------------------- 接口契约


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


def _feedback_data(**overrides: Any) -> ReportGenFeedbackData:
    payload = {
        "id": str(uuid4()),
        "job_id": str(uuid4()),
        "slot_key": None,
        "content": "结果与讨论写细一点",
        "status": "open",
        "applied_job_id": None,
        "created_at": NOW,
    }
    payload.update(overrides)
    return ReportGenFeedbackData(**payload)


async def test_create_feedback_endpoint_returns_201(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_id = uuid4()

    async def _create(_db, _job_id, _payload, _user):  # noqa: ANN001, ANN202
        return _feedback_data(job_id=str(job_id))

    monkeypatch.setattr(service_module, "create_feedback", _create)

    response = await client.post(
        f"/api/v1/research/report-gen/jobs/{job_id}/feedback",
        json={"content": "结果与讨论写细一点"},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["data"]["status"] == "open"
    assert body["message"] == "意见已记录，下次生成会参考"


async def test_list_feedback_endpoint_returns_open_count(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    job_id = uuid4()

    async def _list(_db, _job_id):  # noqa: ANN001, ANN202
        return ReportGenFeedbackListData(total=1, open_count=1, items=[_feedback_data()])

    monkeypatch.setattr(service_module, "list_feedback", _list)

    response = await client.get(f"/api/v1/research/report-gen/jobs/{job_id}/feedback")

    assert response.status_code == 200
    assert response.json()["data"]["open_count"] == 1


async def test_update_feedback_endpoint_returns_new_status(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    feedback_id = uuid4()

    async def _update(_db, _feedback_id, payload, _user):  # noqa: ANN001, ANN202
        return _feedback_data(id=str(feedback_id), status=payload.status)

    monkeypatch.setattr(service_module, "update_feedback", _update)

    response = await client.patch(
        f"/api/v1/research/report-gen/feedback/{feedback_id}",
        json={"status": "ignored"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ignored"


async def test_promote_endpoint_returns_promoted_source(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    feedback_id = uuid4()

    async def _promote(_db, _feedback_id, _user):  # noqa: ANN001, ANN202
        return ReportGenExamplePromoteData(
            feedback_id=str(_feedback_id),
            slot_key="study_conclusion",
            slot_label="研究结论",
            value="收率 92%",
            source="feedback_promoted",
            created=True,
        )

    monkeypatch.setattr(service_module, "promote_feedback", _promote)

    response = await client.post(f"/api/v1/research/report-gen/feedback/{feedback_id}/promote")

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["source"] == "feedback_promoted"
    assert body["message"] == "已存成示例写法，以后生成会参考"
