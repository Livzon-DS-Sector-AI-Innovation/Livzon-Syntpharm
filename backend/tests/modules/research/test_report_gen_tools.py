"""Agent 工具集的单元测试：写保护、批量上限、来源登记与引用源。

工具是模型唯一能改文档的入口，所以这里不测「模型会不会用」，只测「用了之后能不能越权」：
- 标题段/固定文字段/签字区必须拒绝并给出可读原因；
- 一次超过批量上限必须整批拒绝（不能写一半再报错）；
- 写入时的 source_ids 要落到记录里，引用源必须与正文写入一一对应；
- 追加段落的 seq 要单调，出稿回放才能保持顺序。
"""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

from docx import Document
from docx.document import Document as DocxDocument

from app.modules.research.report_gen.outline import build_outline
from app.modules.research.report_gen.structure import open_document
from app.modules.research.report_gen.tools import ReportGenRuntime


class _Session:
    """只记录 add() 的最小 session 替身：写工具只落 ORM 行，不查库。"""

    def __init__(self) -> None:
        self.added: list[Any] = []

    def add(self, row: Any) -> None:
        self.added.append(row)


def _docx(document: DocxDocument) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _template() -> DocxDocument:
    document = Document()
    document.add_paragraph("1 项目概况", style="Heading 1")
    document.add_paragraph("")  # p1 可写
    document.add_paragraph("固定说明文字")  # p2 不可写
    placeholder = document.add_paragraph()
    placeholder.add_run("品种名称：")
    placeholder.add_run("____")
    document.add_paragraph("2 试验数据", style="Heading 1")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "结果"
    table.cell(1, 0).text = "纯度"
    table.cell(1, 1).text = ""
    return document


def _fixed_template() -> DocxDocument:
    """正文后可写、附件整章禁写，用于验证追加类工具也受固定章节约束。"""
    document = Document()
    document.add_paragraph("1 正文", style="Heading 1")
    document.add_paragraph("")
    document.add_paragraph("附件", style="Heading 1")
    document.add_paragraph("")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "附件材料"
    table.cell(0, 1).text = "份数"
    return document


def _carried_row(key: str, value: str, *, anchor: dict[str, Any] | None = None) -> Any:
    """上一版人工确认后带进本任务的行：anchor 里带 human_locked 标记。"""
    return SimpleNamespace(
        slot_key=key,
        slot_label=f"人工确认-{key}",
        anchor=anchor or {"kind": "paragraph", "human_locked": True},
        value=value,
        state="filled",
        edit_source="manual",
    )


def _runtime(
    *,
    batch_limit: int = 10,
    document: DocxDocument | None = None,
    rows: dict[str, Any] | None = None,
) -> ReportGenRuntime:
    outline = build_outline(open_document(_docx(document or _template())))
    config = SimpleNamespace(
        write_batch_limit=batch_limit,
        search_query_limit=5,
        kb_top_k=6,
        disabled_tools=frozenset(),
    )
    job = SimpleNamespace(id=uuid4(), doc_code=None, drug_name=None, supplement_text=None)
    project = SimpleNamespace(id=uuid4(), name="测试项目")
    runtime = ReportGenRuntime(
        cast(Any, _Session()),
        cast(Any, job),
        cast(Any, project),
        outline,
        rows or {},
        cast(Any, config),
    )
    # 模拟检索阶段登记过的来源
    runtime.sources["s1"] = {"source_name": "小试报告.pdf", "evidence": "纯度 99.2%"}
    runtime.sources["s2"] = {"source_name": "工艺规程.docx", "evidence": "步骤 3.2"}
    return runtime


def test_write_paragraph_allows_label_append() -> None:
    """「标签：」段不再被当成固定文字拒绝；行里要带 append 标记，渲染时才不会冲掉标签。"""
    document = _template()
    document.add_paragraph("制剂/规格：")
    runtime = _runtime(document=document)

    outcome = runtime.write_paragraph({"items": [{"index": 5, "text": "片剂 10mg", "source_ids": ["s1"]}]})

    assert outcome.ok is True
    row = runtime.slot_rows["p5"]
    assert row.value == "片剂 10mg"
    assert (row.anchor or {}).get("append") is True


def test_write_paragraph_rejects_heading_and_fixed_text() -> None:
    runtime = _runtime()
    outcome = runtime.write_paragraph({"items": [{"index": 0, "text": "改标题"}, {"index": 2, "text": "覆盖固定文字"}]})
    assert outcome.ok is False
    assert outcome.payload["written"] == 0
    errors = " ".join(str(item) for item in outcome.payload["errors"])
    assert "标题" in errors
    assert "完整内容" in errors
    assert runtime.rejected == 2
    assert runtime.slot_rows == {}


def test_write_paragraph_writes_blank_and_placeholder() -> None:
    runtime = _runtime()
    outcome = runtime.write_paragraph(
        {
            "items": [
                {"index": 1, "text": "项目概况正文", "source_ids": ["s1"]},
                {"index": 3, "text": "阿莫西林", "source_ids": ["s2"]},
            ]
        }
    )
    assert outcome.ok is True
    assert outcome.payload["written"] == 2
    row = runtime.slot_rows["p1"]
    assert row.value == "项目概况正文"
    assert row.state == "filled"
    assert row.source_name == "小试报告.pdf"
    assert (row.anchor or {})["location"] == "正文第2段"
    # 同一位置重复写入只保留一条记录（引用源不会重复计数）
    runtime.write_paragraph({"items": [{"index": 1, "text": "改后的正文", "source_ids": ["s2"]}]})
    assert len(runtime.slot_rows) == 2
    assert runtime.slot_rows["p1"].value == "改后的正文"


def test_batch_limit_rejects_whole_call() -> None:
    runtime = _runtime(batch_limit=2)
    outcome = runtime.write_paragraph(
        {"items": [{"index": 1, "text": "a"}, {"index": 3, "text": "b"}, {"index": 1, "text": "c"}]}
    )
    assert outcome.ok is False
    assert "最多写 2 处" in outcome.summary
    assert runtime.slot_rows == {}


def test_write_cell_and_append_rows() -> None:
    runtime = _runtime()
    cell = runtime.write_cell({"items": [{"table_index": 0, "row": 1, "col": 1, "text": "99.2%"}]})
    assert cell.ok is True
    assert runtime.slot_rows["t0r1c1"].value == "99.2%"
    # 表头不给写
    header = runtime.write_cell({"items": [{"table_index": 0, "row": 0, "col": 0, "text": "x"}]})
    assert header.ok is False

    rows = runtime.append_table_rows(
        {"table_index": 0, "clone_from_row": 1, "items": [{"cells": ["杂质", "0.1%"], "source_ids": ["s1"]}]}
    )
    assert rows.ok is True
    anchor = runtime.slot_rows["at1"].anchor or {}
    assert anchor["kind"] == "append_table_rows"
    assert anchor["rows"][0]["cells"] == ["杂质", "0.1%"]
    assert anchor["clone_from_row"] == 1


def test_append_paragraph_increments_seq_and_inherits_clone() -> None:
    runtime = _runtime()
    first = runtime.append_paragraph({"after": "p4", "items": [{"text": "路线五", "clone_from": 4}]})
    second = runtime.append_paragraph({"after": "ap1", "items": [{"text": "路线五内容", "clone_from": 3}]})
    assert first.ok and second.ok
    assert (runtime.slot_rows["ap1"].anchor or {})["seq"] == 1
    assert (runtime.slot_rows["ap2"].anchor or {})["seq"] == 2
    assert (runtime.slot_rows["ap2"].anchor or {})["after"] == "ap1"


def test_append_paragraph_requires_known_anchor_and_clone() -> None:
    runtime = _runtime()
    outcome = runtime.append_paragraph({"after": "p99", "items": [{"text": "x", "clone_from": 1}]})
    assert outcome.ok is False
    assert runtime.slot_rows == {}


def test_append_rejects_fixed_sections() -> None:
    """追加也是写：附件/签字区不能被当作插入点，附件里的表格也不能加行。"""
    runtime = _runtime(document=_fixed_template())
    paragraph = runtime.append_paragraph({"after": "p2", "items": [{"text": "塞进附件", "clone_from": 1}]})
    assert paragraph.ok is False
    assert "禁写" in paragraph.summary
    rows = runtime.append_table_rows({"table_index": 0, "items": [{"cells": ["a", "b"]}]})
    assert rows.ok is False
    assert "禁写" in rows.summary
    assert runtime.slot_rows == {}


def test_references_dedupe_by_source_and_are_idempotent() -> None:
    runtime = _runtime()
    runtime.write_paragraph(
        {
            "items": [
                {"index": 1, "text": "概况", "source_ids": ["s1"]},
                {"index": 3, "text": "品种", "source_ids": ["s1", "s2"]},
            ]
        }
    )
    runtime.write_cell({"items": [{"table_index": 0, "row": 1, "col": 1, "text": "99.2%", "source_ids": ["s1"]}]})

    first = runtime.write_references()
    assert first.ok is True
    entries = runtime.slot_rows["ref"].value.split("\n") if runtime.slot_rows["ref"].value else []
    assert len(entries) == 2
    assert entries[0].startswith("[1] 小试报告.pdf（用于：")
    assert "正文第2段" in entries[0]
    assert "表1第2行第2列" in entries[0]
    assert entries[1].startswith("[2] 工艺规程.docx（用于：")
    # 重复调用不新增第二条引用源
    assert runtime.write_references().payload["duplicated"] is True


def test_references_without_source_is_refused() -> None:
    runtime = _runtime()
    runtime.write_paragraph({"items": [{"index": 1, "text": "无出处"}]})
    outcome = runtime.write_references()
    assert outcome.ok is False
    assert "ref" not in runtime.slot_rows


def test_human_locked_position_is_not_rewritten() -> None:
    """人工确认过的位置：AI 写入必须被拒，且不能计入「模型违规次数」。"""
    runtime = _runtime(rows={"p1": _carried_row("p1", "人工定稿正文")})

    outcome = runtime.write_paragraph({"items": [{"index": 1, "text": "AI 想覆盖"}]})

    assert outcome.ok is False
    assert runtime.rejected == 0
    assert runtime.slot_rows["p1"].value == "人工定稿正文"
    errors = " ".join(str(item) for item in outcome.payload["errors"])
    assert "人工确认" in errors


def test_read_outline_excludes_human_locked_and_reports_count() -> None:
    runtime = _runtime(rows={"p1": _carried_row("p1", "人工定稿正文")})

    outcome = runtime.read_template_outline({})

    keys = [item["key"] for item in outcome.payload["items"]]
    assert "p1" not in keys
    assert outcome.payload["human_locked_total"] == 1
    assert outcome.payload["writable_total"] == runtime.outline.writable_total - 1
    assert "人工已确认 1 处" in outcome.summary


def test_append_skips_human_locked_seq() -> None:
    """人工确认的追加段占了 ap1：AI 追加必须换 key，不能覆盖人工内容。"""
    locked = _carried_row(
        "ap1",
        "人工追加的说明",
        anchor={"kind": "append_paragraph", "after": "p4", "seq": 1, "location": "追加段落1", "human_locked": True},
    )
    runtime = _runtime(rows={"ap1": locked})

    outcome = runtime.append_paragraph({"after": "p4", "items": [{"text": "AI 追加", "clone_from": 1}]})

    assert outcome.ok is True
    assert runtime.slot_rows["ap1"].value == "人工追加的说明"
    assert (runtime.slot_rows["ap2"].anchor or {})["seq"] == 2


def test_coverage_counts_written_and_unwritten() -> None:
    runtime = _runtime()
    runtime.write_paragraph({"items": [{"index": 1, "text": "概况", "source_ids": ["s1"]}]})
    runtime.write_cell({"items": [{"table_index": 0, "row": 1, "col": 1, "text": "99", "source_ids": ["s1"]}]})
    coverage = runtime.coverage()
    assert coverage["written"] == 2
    assert coverage["unwritten"] == coverage["writable_total"] - 2
    assert "p3" in coverage["unwritten_sample"]
    finalized = runtime.finalize({"summary": "完成"})
    assert "已写 2/" in finalized.summary
    assert runtime.finalized is True
