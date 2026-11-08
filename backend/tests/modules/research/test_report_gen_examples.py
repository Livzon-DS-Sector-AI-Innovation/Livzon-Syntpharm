"""示例库维护与补充说明还原的单元测试。

不连数据库、不调 LLM：
- 还原：重新生成时能把上次拼进去的意见段剥掉，只留用户原话；
- 管理：列表按启用数统计、改值、停用、软删除、找不到时报 404 语义的异常；
- 带入：详情页能按 applied_job_id 反查这一版带走了哪几条意见；
- 接口：GET/PATCH/DELETE 的状态码与响应外壳。
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
from app.core.exceptions import NotFoundException
from app.modules.research.models import RdReportGenExample
from app.modules.research.report_gen import service as service_module
from app.modules.research.report_gen.api import router as report_gen_router
from app.modules.research.report_gen.feedback import merge_supplement, strip_merged
from app.modules.research.report_gen.schemas import (
    ReportGenExampleData,
    ReportGenExampleListData,
    ReportGenExampleUpdateRequest,
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

    def __init__(self, *, example: Any = None, rows: list[Any] | None = None) -> None:
        self.example = example
        self.rows = rows or []
        self.commits = 0

    async def get(self, model: Any, _pk: Any) -> Any:
        if model is RdReportGenExample:
            return self.example
        return None

    async def execute(self, _stmt: Any) -> _Result:
        return _Result(self.rows)

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, _obj: Any) -> None:
        return None


def _example_row(**overrides: Any) -> Any:
    row = SimpleNamespace(
        id=uuid4(),
        template_id=uuid4(),
        slot_key="result_discussion",
        slot_label="结果与讨论",
        source="feedback_promoted",
        value="本品在加速条件下 6 个月稳定",
        evidence_text="评审意见：写具体周期",
        usage_count=3,
        is_active=True,
        is_deleted=False,
        updated_at=NOW,
    )
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


def _feedback_item(**overrides: Any) -> Any:
    item = SimpleNamespace(slot_key="result_discussion", content="把周期写具体")
    for key, value in overrides.items():
        setattr(item, key, value)
    return item


# ---------------------------------------------------------------- 还原补充说明


def test_strip_merged_removes_appended_feedback_block() -> None:
    merged = merge_supplement("多写一点数据", [_feedback_item()])

    assert "【上一版评审意见" in merged
    assert strip_merged(merged) == "多写一点数据"


def test_strip_merged_keeps_plain_text() -> None:
    assert strip_merged("  只看结论  ") == "只看结论"


def test_strip_merged_handles_none() -> None:
    assert strip_merged(None) == ""


def test_strip_merged_keeps_text_when_only_header_present() -> None:
    merged = merge_supplement(None, [_feedback_item()])

    assert strip_merged(merged) == ""


# ---------------------------------------------------------------- 带入意见反查


async def test_applied_feedback_reads_rows() -> None:
    feedback_id = uuid4()
    session = _Session(rows=[(feedback_id, "result_discussion", "写具体周期")])

    items = await service_module._applied_feedback(session, uuid4())

    assert len(items) == 1
    assert items[0].id == feedback_id
    assert items[0].slot_key == "result_discussion"


# ---------------------------------------------------------------- 示例库管理


async def test_list_examples_counts_active() -> None:
    rows = [_example_row(), _example_row(slot_key="conclusion", is_active=False)]

    data = await service_module.list_examples(_Session(rows=rows), uuid4())

    assert data.total == 2
    assert data.active_total == 1


async def test_update_example_changes_value_and_deactivates() -> None:
    row = _example_row()
    session = _Session(example=row)

    data = await service_module.update_example(
        session,
        row.id,
        ReportGenExampleUpdateRequest(value="  新写法  ", is_active=False),
        None,
    )

    assert data.value == "新写法"
    assert data.is_active is False
    assert session.commits == 1


async def test_update_example_keeps_value_when_blank() -> None:
    row = _example_row()
    session = _Session(example=row)

    data = await service_module.update_example(
        session,
        row.id,
        ReportGenExampleUpdateRequest(value="   "),
        None,
    )

    assert data.value == "本品在加速条件下 6 个月稳定"
    assert session.commits == 1


async def test_update_example_raises_when_missing() -> None:
    with pytest.raises(NotFoundException):
        await service_module.update_example(
            _Session(example=None),
            uuid4(),
            ReportGenExampleUpdateRequest(value="x"),
            None,
        )


async def test_delete_example_soft_deletes_and_deactivates() -> None:
    row = _example_row()
    session = _Session(example=row)

    data = await service_module.delete_example(session, row.id, None)

    assert row.is_deleted is True
    assert row.is_active is False
    assert data.is_active is False
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


def _example_data(**overrides: Any) -> ReportGenExampleData:
    payload = {
        "id": str(uuid4()),
        "template_id": str(uuid4()),
        "slot_key": "result_discussion",
        "slot_label": "结果与讨论",
        "source": "feedback_promoted",
        "value": "本品在加速条件下 6 个月稳定",
        "evidence_text": "评审意见：写具体周期",
        "usage_count": 3,
        "is_active": True,
        "updated_at": NOW,
    }
    payload.update(overrides)
    return ReportGenExampleData(**payload)


async def test_list_examples_endpoint_returns_items(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _list(_db, _template_id, **_kwargs):  # noqa: ANN001, ANN003, ANN202
        return ReportGenExampleListData(total=1, active_total=1, items=[_example_data()])

    monkeypatch.setattr(service_module, "list_examples", _list)

    response = await client.get(f"/api/v1/research/report-gen/templates/{uuid4()}/examples")

    assert response.status_code == 200
    assert response.json()["data"]["active_total"] == 1


async def test_update_example_endpoint_returns_updated_row(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    example_id = uuid4()

    async def _update(_db, _example_id, _payload, _user):  # noqa: ANN001, ANN202
        return _example_data(id=str(example_id), is_active=False)

    monkeypatch.setattr(service_module, "update_example", _update)

    response = await client.patch(
        f"/api/v1/research/report-gen/examples/{example_id}",
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["data"]["is_active"] is False
    assert response.json()["message"] == "已更新"


async def test_delete_example_endpoint_returns_removed_row(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    example_id = uuid4()

    async def _delete(_db, _example_id, _user):  # noqa: ANN001, ANN202
        return _example_data(id=str(example_id), is_active=False)

    monkeypatch.setattr(service_module, "delete_example", _delete)

    response = await client.delete(f"/api/v1/research/report-gen/examples/{example_id}")

    assert response.status_code == 200
    assert response.json()["message"] == "已删除"
