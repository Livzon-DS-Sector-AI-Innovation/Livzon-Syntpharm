"""人工修改的延续：新任务继承上一版人工值，母本换版时按指纹跳过。

不连数据库：查询结果用假 session 预置，母本读取替换成内存 docx。
这里只钉住判断逻辑——哪些能带、哪些必须跳过、带过去之后 AI 是否写不进去。
"""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from docx import Document

from app.modules.research.report_gen import service as service_module
from app.modules.research.report_gen.outline import build_outline
from app.modules.research.report_gen.structure import open_document


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
    def __init__(self, results: list[list[Any]]) -> None:
        self.results = list(results)
        self.added: list[Any] = []
        self.flushes = 0

    async def execute(self, _stmt: Any) -> _Result:
        if not self.results:
            raise AssertionError("没有预置更多查询结果")
        return _Result(self.results.pop(0))

    def add(self, obj: Any) -> None:
        self.added.append(obj)

    async def flush(self) -> None:
        self.flushes += 1


def _docx_bytes(document: Any) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _template() -> bytes:
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    document.add_paragraph("")
    document.add_paragraph("固定说明文字")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "内容"
    table.cell(1, 0).text = "结论"
    document.add_paragraph("2 结论", style="Heading 1")
    document.add_paragraph("")
    return _docx_bytes(document)


def _job() -> Any:
    return SimpleNamespace(
        id=uuid4(),
        report_id=uuid4(),
        deliverable_template_id=uuid4(),
        template_file_key="local:doc-gen/job/template.docx",
    )


def _previous_job() -> Any:
    return SimpleNamespace(id=uuid4(), created_at=None)


def _slot(key: str, *, value: str, anchor: dict[str, Any], label: str | None = None) -> Any:
    return SimpleNamespace(
        slot_key=key,
        slot_label=label or key,
        anchor=anchor,
        value=value,
        source_name="实验记录.xlsx",
        evidence="纯度 99.2%",
        confidence=0.9,
    )


def _position_anchor(key: str) -> dict[str, Any]:
    outline = build_outline(open_document(_template()))
    return outline.by_key()[key].anchor()


async def _carry(session: Any, job: Any) -> int:
    """假 session/模板替身只实现被测路径，类型上按 Any 放行。"""
    return await service_module._carry_over_manual_slots(
        cast(Any, session), cast(Any, job), cast(Any, SimpleNamespace()), None
    )


@pytest.fixture(autouse=True)
def _patch_template(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(service_module, "load_template_bytes", lambda _j, _tpl: _template())


async def test_no_previous_job_means_nothing_to_carry() -> None:
    session = _Session([[]])
    job = _job()

    carried = await _carry(session, job)

    assert carried == 0
    assert not session.added


async def test_matching_position_is_carried_as_human_locked() -> None:
    job = _job()
    session = _Session([[_previous_job()], [_slot("p1", value="人工定稿正文", anchor=_position_anchor("p1"))]])

    carried = await _carry(session, job)

    assert carried == 1
    row = session.added[0]
    assert row.job_id == job.id
    assert row.slot_key == "p1"
    assert row.value == "人工定稿正文"
    assert row.state == "filled"
    assert row.edit_source == "manual"
    assert (row.anchor or {}).get("human_locked") is True
    assert row.source_name == "实验记录.xlsx"


async def test_template_changed_skips_mismatched_fingerprint() -> None:
    job = _job()
    anchor = _position_anchor("p1")
    anchor["fingerprint"] = "stale-fingerprint"
    session = _Session([[_previous_job()], [_slot("p1", value="旧值", anchor=anchor)]])

    carried = await _carry(session, job)

    assert carried == 0
    assert not session.added


async def test_unknown_position_is_skipped() -> None:
    job = _job()
    session = _Session([[_previous_job()], [_slot("p99", value="幽灵位置", anchor={})]])

    assert await _carry(session, job) == 0


async def test_append_paragraph_is_renumbered_and_keeps_anchor_chain() -> None:
    job = _job()
    anchor = {"kind": "append_paragraph", "after": "p4", "seq": 1, "location": "追加段落1"}
    session = _Session([[_previous_job()], [_slot("ap1", value="人工追加说明", anchor=anchor)]])

    carried = await _carry(session, job)

    assert carried == 1
    row = session.added[0]
    assert row.slot_key == "ap1"
    assert (row.anchor or {})["after"] == "p4"
    assert (row.anchor or {})["seq"] == 1
    assert (row.anchor or {})["human_locked"] is True


async def test_append_paragraph_with_stale_anchor_is_skipped() -> None:
    job = _job()
    anchor = {"kind": "append_paragraph", "after": "p99", "seq": 1}
    session = _Session([[_previous_job()], [_slot("ap1", value="人工追加说明", anchor=anchor)]])

    assert await _carry(session, job) == 0


async def test_appended_table_rows_are_kept_when_table_exists() -> None:
    job = _job()
    anchor = {"kind": "append_table_rows", "table_index": 0, "rows": [{"cells": ["收率", "92%"]}], "seq": 1}
    session = _Session([[_previous_job()], [_slot("at1", value="收率\n92%", anchor=anchor)]])

    carried = await _carry(session, job)

    assert carried == 1
    assert session.added[0].slot_key == "at1"
    assert (session.added[0].anchor or {})["human_locked"] is True


async def test_appended_table_rows_skipped_when_table_missing() -> None:
    job = _job()
    anchor = {"kind": "append_table_rows", "table_index": 9, "rows": [{"cells": ["x"]}], "seq": 1}
    session = _Session([[_previous_job()], [_slot("at1", value="x", anchor=anchor)]])

    assert await _carry(session, job) == 0


async def test_empty_value_is_not_carried() -> None:
    """空值不继承：人工清空一处等于「这次不要内容」，带过去会把空行也固定住。"""
    job = _job()
    session = _Session([[_previous_job()], [_slot("p1", value="   ", anchor=_position_anchor("p1"))]])

    assert await _carry(session, job) == 0
