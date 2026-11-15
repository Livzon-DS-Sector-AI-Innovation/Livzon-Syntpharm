"""详情页审阅清单：装配逻辑与接口契约。

清单的价值全在「合并」这一步：``rd_report_gen_slots`` 只记写过的位置，未写位置没有行。
这里把三件事钉住——未写位置必须出现、表格归属按表前那一段算、追加内容排在文末。
"""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from docx import Document
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.core.database import get_db
from app.modules.research import models as research_models
from app.modules.research.report_gen import review as review_module
from app.modules.research.report_gen.api import router as report_gen_router
from app.modules.research.report_gen.outline import TemplateOutline, build_outline
from app.modules.research.report_gen.schemas import (
    ReportGenFieldItemData,
    ReportGenOutlineData,
    ReportGenOutlineStatsData,
)
from app.platform.identity.deps import require_current_user
from app.platform.permission.service.authorization import PermissionContext


class _FakeScalars:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def all(self) -> list[Any]:
        return self._rows


class _FakeResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _FakeScalars:
        return _FakeScalars(self._rows)


class _FakeSession:
    """只实现 review 用到的两个入口：按主键取任务/模板、查 slots。"""

    def __init__(self, job: Any, template: Any = None, rows: list[Any] | None = None) -> None:
        self._job = job
        self._template = template
        self._rows = rows or []

    async def get(self, model: Any, key: Any) -> Any:
        if model is research_models.RdReportGenJob:
            return self._job
        if model is research_models.RdDeliverableTemplate:
            return self._template
        return None

    async def execute(self, statement: Any) -> _FakeResult:
        return _FakeResult(self._rows)


def _docx_bytes(document: Any) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _template() -> bytes:
    """母本：两个一级标题、一个空段、一段固定说明、一张 2×2 表（右下角留空）。"""
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    document.add_paragraph("")  # p1 可写
    document.add_paragraph("本段为固定说明文字")  # p2 不可写
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "内容"
    table.cell(1, 0).text = "结论"
    document.add_paragraph("2 结论", style="Heading 1")  # p3
    document.add_paragraph("")  # p4 可写
    return _docx_bytes(document)


def _job(job_id: UUID, *, document_key: str | None = None) -> Any:
    return SimpleNamespace(
        id=job_id,
        is_deleted=False,
        deliverable_template_id=None,
        template_file_key="local:doc-gen/job/template.docx",
        template_file_name="母本.docx",
        document_object_key=document_key,
        document_file_name="报告.docx" if document_key else None,
        status="completed",
    )


def _slot(
    job_id: UUID,
    key: str,
    *,
    value: str | None,
    state: str = "filled",
    anchor: dict[str, Any] | None = None,
    source_name: str | None = None,
) -> Any:
    return SimpleNamespace(
        job_id=job_id,
        slot_key=key,
        slot_label="",
        anchor=anchor or {},
        value=value,
        state=state,
        source_name=source_name,
        evidence=None,
        confidence=None,
        edit_source=None,
        is_deleted=False,
    )


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    review_module.clear_cache()


def _patch_store(monkeypatch: pytest.MonkeyPatch, *, document_bytes: bytes | None = None) -> bytes:
    template_bytes = _template()

    def _load(key: str) -> bytes | None:
        if key.endswith("template.docx"):
            return template_bytes
        if document_bytes is not None and key.endswith("report.docx"):
            return document_bytes
        return None

    monkeypatch.setattr("app.modules.research.doc_template.store.load_bytes", _load)
    return template_bytes


async def _review(job: Any, rows: list[Any], template: Any = None) -> ReportGenOutlineData:
    session = _FakeSession(job, template, rows)
    return await review_module.build_review(cast(Any, session), job.id)


async def test_written_and_unwritten_positions_are_merged(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_store(monkeypatch)
    job_id = uuid4()
    job = _job(job_id)
    rows = [
        _slot(
            job_id,
            "p1",
            value="6 批实验数据汇总",
            anchor={"kind": "paragraph", "index": 1, "location": "正文第 2 段"},
            source_name="实验记录.xlsx",
        )
    ]

    data = await _review(job, rows)

    items = {item.key: item for item in data.items}
    # 母本全部位置都进清单：固定内容只是 AI 不写，人工仍可改
    assert set(items) == {
        "p0",
        "p1",
        "p2",
        "p3",
        "p4",
        "t0r0c0",
        "t0r0c1",
        "t0r1c0",
        "t0r1c1",
    }
    assert data.locked_items == []
    assert all(item.editable for item in data.items)
    assert items["p1"].state == "written"
    assert items["p1"].source_name == "实验记录.xlsx"
    # 未写位置也必须出现，并说明原因
    assert items["p4"].state == "blank"
    assert "没有写入" in (items["p4"].reason or "")
    assert items["p2"].writable is False
    assert items["p2"].state == "blank"
    assert "母本固定内容" in (items["p2"].reason or "")
    assert data.stats.writable_total == 3
    assert data.stats.written == 1
    assert data.stats.blank == 2
    assert data.stats.locked == 6
    assert data.stats.coverage_rate == pytest.approx(0.3333)

    # 表格归到表前那一段所在的章节，而不是后面的「2 结论」
    assert items["t0r1c1"].section == "1 数据"
    assert items["p4"].section == "2 结论"


async def test_pending_row_needs_verify(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_store(monkeypatch)
    job_id = uuid4()
    rows = [_slot(job_id, "p1", value="暂无来源的结论", state="pending")]

    data = await _review(_job(job_id), rows)

    item = next(item for item in data.items if item.key == "p1")
    assert item.state == "needs_verify"
    assert data.stats.needs_verify == 1
    assert data.stats.written == 1


async def test_references_are_separate_from_items(monkeypatch: pytest.MonkeyPatch) -> None:
    """参考资料不进位置清单：它不在文档里，混进 items 会让预览多标一处、统计也虚高。"""
    _patch_store(monkeypatch)
    job_id = uuid4()
    rows = [
        _slot(
            job_id,
            "p1",
            value="6 批实验数据汇总",
            anchor={"kind": "paragraph", "index": 1, "location": "正文第 2 段"},
            source_name="实验记录.xlsx",
        ),
        _slot(
            job_id,
            "ap1",
            value="补充：本批数据按 2026 版方法计算",
            anchor={"kind": "append_paragraph", "location": "文末第1段", "source_names": ["实验记录.xlsx"]},
        ),
        _slot(
            job_id,
            "ref",
            value="[1] 实验记录.xlsx（用于：正文第 2 段）",
            anchor={"kind": "references", "location": "参考资料"},
        ),
    ]

    data = await _review(_job(job_id), rows)

    assert "ref" not in [item.key for item in data.items]
    assert data.items[-1].key == "ap1"
    assert data.stats.appended == 1
    # 参考资料由写入记录现算：来源只有一条，落点包含正文段落与追加段
    assert data.stats.references == 1
    assert len(data.references) == 1
    group = data.references[0]
    assert group.name == "实验记录.xlsx"
    assert group.total == 2
    locations = {item.key: item.label for item in group.locations}
    assert locations["p1"] == "正文第 2 段"
    assert "ap1" not in locations  # 追加段定位到它依附的位置
    assert locations[None] == "文末第1段"


async def test_document_stats_come_from_current_docx(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_store(monkeypatch, document_bytes=_template())
    job_id = uuid4()
    job = _job(job_id, document_key="local:doc-gen/job/report.docx")

    data = await _review(job, [])

    assert data.has_document is True
    assert data.template_paragraph_count == 5
    assert data.template_table_count == 1
    assert data.document_paragraph_count == 5
    assert data.document_table_count == 1
    # 段落文本是前端按内容对齐的依据：docx-preview 会拆分页符段落，光靠下标会错位
    assert len(data.document_paragraph_texts) == 5
    assert data.document_paragraph_texts[0] == "1 数据"


async def test_outline_is_parsed_once_per_template(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_store(monkeypatch)
    job_id = uuid4()
    calls = {"count": 0}
    real_build = build_outline

    def _counting(document: Any) -> TemplateOutline:
        calls["count"] += 1
        return real_build(document)

    monkeypatch.setattr(review_module, "build_outline", _counting)

    await _review(_job(job_id), [])
    await _review(_job(job_id), [])

    assert calls["count"] == 1


@pytest.fixture
async def client(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(report_gen_router, prefix="/api/v1/research/report-gen")

    user = SimpleNamespace(id=uuid4())
    app.dependency_overrides[require_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: SimpleNamespace()

    async def _fake_context(db, current_user, code):  # noqa: ANN001, ANN202
        return PermissionContext(user=current_user, permission_code=code)

    monkeypatch.setattr("app.platform.permission.deps.build_permission_context", _fake_context)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as async_client:
        yield async_client


async def test_outline_api_returns_envelope(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    job_id = uuid4()

    async def _build(db, target_job_id):  # noqa: ANN001, ANN202
        return ReportGenOutlineData(
            job_id=target_job_id,
            status="completed",
            has_document=True,
            stats=ReportGenOutlineStatsData(writable_total=2, written=1, blank=1),
            items=[
                ReportGenFieldItemData(
                    key="p1",
                    kind="paragraph",
                    section="1 数据",
                    section_index=0,
                    label="正文第 2 段",
                    order=10,
                    state="written",
                    value="6 批实验数据汇总",
                )
            ],
        )

    monkeypatch.setattr(review_module, "build_review", _build)

    response = await client.get(f"/api/v1/research/report-gen/jobs/{job_id}/outline")

    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["stats"]["writable_total"] == 2
    assert payload["items"][0]["key"] == "p1"
    assert payload["items"][0]["state"] == "written"
