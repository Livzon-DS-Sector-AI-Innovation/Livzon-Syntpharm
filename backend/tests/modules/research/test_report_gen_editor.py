"""在线编辑：七类操作、全量可编辑、校验失败逐条还原、结构性删除仍受限。

原则有两条：
1. **宁可不改，也不能改错位置**——锚点失效、内容为空/超长时这一处必须回到母本原样；
2. **一处写坏不能拖垮整批**——其余合法操作照常落版本，被丢弃的操作逐条返回原因。
"""

from __future__ import annotations

from io import BytesIO
from types import SimpleNamespace
from typing import Any

import pytest
from docx import Document

from app.modules.research.report_gen.editor import apply_operations
from app.modules.research.report_gen.outline import build_outline
from app.modules.research.report_gen.schemas import ReportGenEditOperationRequest
from app.modules.research.report_gen.structure import open_document


def _docx_bytes(document: Any) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _template() -> bytes:
    """母本：p0 标题 / p1 空 / p2 固定说明 / 2×2 表（右下留空）/ p3 二级标题 / p4 空。"""
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    document.add_paragraph("")
    document.add_paragraph("本段为固定说明文字")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "内容"
    table.cell(1, 0).text = "结论"
    document.add_paragraph("2 结论", style="Heading 1")
    document.add_paragraph("")
    return _docx_bytes(document)


def _short_template() -> bytes:
    """结构对不上的成品：用来验证锚点失效必须被拒，而不是写到别的段落上。"""
    document = Document()
    document.add_paragraph("只有一段")
    return _docx_bytes(document)


def _fixed_section_template() -> bytes:
    """签字审批区（母本固定内容）里放一张表：AI 不写，但人工应该能加行。"""
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    document.add_paragraph("")
    document.add_paragraph("签字审批", style="Heading 1")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "角色"
    table.cell(0, 1).text = "签字"
    table.cell(1, 0).text = "审核人"
    table.cell(1, 1).text = ""
    return _docx_bytes(document)


def _outline(data: bytes):
    return build_outline(open_document(data))


def _paragraphs(data: bytes) -> list[str]:
    return [paragraph.text for paragraph in open_document(data).paragraphs]


def _slot(
    key: str,
    *,
    value: str | None,
    anchor: dict[str, Any] | None = None,
    label: str = "",
) -> Any:
    return SimpleNamespace(
        slot_key=key,
        slot_label=label or key,
        anchor=anchor or {"kind": "append_paragraph", "location": "文末"},
        value=value,
        state="filled",
        edit_source="manual",
    )


def _op(op: str, **kwargs: Any) -> ReportGenEditOperationRequest:
    return ReportGenEditOperationRequest(op=op, **kwargs)


def _run(
    operations: list[ReportGenEditOperationRequest],
    *,
    document: bytes | None = None,
    rows: dict[str, Any] | None = None,
    outline: Any = None,
):
    data = document if document is not None else _template()
    # 母本 outline 要跟原件走：拿成品重建会把它当成新母本，标签/占位判定全变
    return apply_operations(data, outline or _outline(data), rows or {}, operations)


def test_update_paragraph_keeps_other_content() -> None:
    run = _run([_op("update_text", key="p1", text="6 批实验数据汇总")])

    assert run.ok is True
    assert run.document is not None
    assert _paragraphs(run.document) == ["1 数据", "6 批实验数据汇总", "本段为固定说明文字", "2 结论", ""]
    change = run.slot_changes[0]
    assert change.key == "p1"
    assert change.operation == "update_text"
    assert change.value == "6 批实验数据汇总"


def test_update_label_keeps_label_and_only_changes_value() -> None:
    document = Document()
    document.add_paragraph("制剂/规格：")
    data = _docx_bytes(document)

    run = _run([_op("update_text", key="p0", text="片剂 10mg")], document=data)

    assert run.ok is True
    assert run.document is not None
    assert _paragraphs(run.document) == ["制剂/规格：片剂 10mg"]
    assert run.slot_changes[0].value == "片剂 10mg"


def test_update_label_again_after_append_can_locate() -> None:
    """追加过值以后锚点文本已变，第二次编辑仍要能定位到同一段。"""
    document = Document()
    document.add_paragraph("制剂/规格：")
    data = _docx_bytes(document)
    outline = _outline(data)

    first = _run([_op("update_text", key="p0", text="片剂 10mg")], document=data)
    assert first.ok is True and first.document is not None

    second = _run(
        [_op("update_text", key="p0", text="胶囊 5mg")],
        document=first.document,
        rows={"p0": _slot("p0", value="片剂 10mg", anchor=outline.by_key()["p0"].anchor())},
        outline=outline,
    )

    assert second.ok is True and second.document is not None
    assert _paragraphs(second.document) == ["制剂/规格：胶囊 5mg"]


def test_update_cell_writes_only_that_cell() -> None:
    run = _run([_op("update_cell", key="t0r1c1", text="收率 92.1%")])

    assert run.ok is True
    assert run.document is not None
    table = open_document(run.document).tables[0]
    assert table.cell(1, 1).text == "收率 92.1%"
    assert table.cell(1, 0).text == "结论"
    assert table.cell(0, 0).text == "项目"


def test_fixed_paragraph_is_now_editable() -> None:
    """母本固定内容只代表 AI 不写，人工编辑必须放开。"""
    run = _run([_op("update_text", key="p2", text="人工改写后的说明")])

    assert run.ok is True
    assert run.applied == 1
    assert run.removals == []
    assert _paragraphs(run.document or b"")[2] == "人工改写后的说明"


def test_fixed_heading_is_editable() -> None:
    run = _run([_op("update_text", key="p0", text="1 数据与结果")])

    assert run.ok is True
    assert _paragraphs(run.document or b"")[0] == "1 数据与结果"


def test_insert_paragraph_after_fixed_position() -> None:
    run = _run([_op("insert_paragraph", key="p2", text="固定说明后的补充")])

    assert run.ok is True
    assert _paragraphs(run.document or b"")[2:4] == ["本段为固定说明文字", "固定说明后的补充"]
    assert run.slot_changes[0].key == "ap1"


def test_insert_paragraph_after_writable_position() -> None:
    run = _run([_op("insert_paragraph", key="p1", text="补充说明一\n补充说明二")])

    assert run.ok is True
    assert run.document is not None
    paragraphs = _paragraphs(run.document)
    assert paragraphs[2:4] == ["补充说明一", "补充说明二"]
    assert run.slot_changes[0].key == "ap1"


def test_delete_appended_paragraph() -> None:
    first = _run([_op("insert_paragraph", key="p1", text="补充说明一")])
    assert first.document is not None
    rows = {"ap1": _slot("ap1", value="补充说明一")}

    second = _run([_op("delete_paragraph", key="ap1")], document=first.document, rows=rows)

    assert second.ok is True
    assert "补充说明一" not in _paragraphs(second.document or b"")
    assert second.slot_changes[0].action == "delete"


def test_append_and_delete_table_row() -> None:
    added = _run([_op("append_table_row", key="t0r1c1", cells=["收率", "92.1%"])])
    assert added.ok is True
    assert added.document is not None
    table = open_document(added.document).tables[0]
    assert len(table.rows) == 3
    assert table.cell(2, 0).text == "收率"
    assert added.slot_changes[0].key == "at1"

    rows = {
        "at1": _slot(
            "at1",
            value="收率\n92.1%",
            anchor={
                "kind": "append_table_rows",
                "table_index": 0,
                "rows": [{"cells": ["收率", "92.1%"]}],
            },
        )
    }
    removed = _run([_op("delete_table_row", key="t0r2c0")], document=added.document, rows=rows)
    assert removed.ok is True
    assert len(open_document(removed.document or b"").tables[0].rows) == 2


def test_append_row_in_fixed_section_is_allowed() -> None:
    """签字审批区是母本固定内容，AI 不写，但人工加一行签字栏应该允许。"""
    template = _fixed_section_template()
    run = apply_operations(
        template,
        _outline(template),
        {},
        [_op("append_table_row", key="t0r1c1", cells=["批准人", ""])],
    )

    assert run.ok is True
    assert run.applied == 1
    table = open_document(run.document or b"").tables[0]
    assert len(table.rows) == 3
    assert table.cell(2, 0).text == "批准人"


def test_delete_empty_template_row_is_allowed() -> None:
    """母本明细表里多出来的空行可以删：内容为空，删掉不改变模板语义。"""
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    document.add_paragraph("")
    table = document.add_table(rows=3, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "内容"
    table.cell(1, 0).text = "结论"
    table.cell(1, 1).text = "已填"
    data = _docx_bytes(document)

    run = _run([_op("delete_table_row", key="t0r2c0")], document=data)

    assert run.ok is True
    assert run.document is not None
    assert len(open_document(run.document).tables[0].rows) == 2


def test_delete_template_paragraph_is_still_rejected() -> None:
    """放开的是「改」，不是「删」：母本段落删掉会破坏版式。"""
    run = _run([_op("delete_paragraph", key="p2")])

    assert run.applied == 0
    assert run.removals[0].reason.startswith("只能删除生成或编辑时新增的段落")
    assert _paragraphs(run.document or b"")[2] == "本段为固定说明文字"


def test_table_header_cannot_be_deleted() -> None:
    run = _run([_op("delete_table_row", key="t0r0c0")])

    assert run.applied == 0
    assert "表头不能删" in run.removals[0].reason


def test_non_empty_template_row_cannot_be_deleted() -> None:
    """母本里有内容的行是模板数据，删了结构就变了：必须拒绝。"""
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    document.add_paragraph("")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "内容"
    table.cell(1, 0).text = "已有数据"
    table.cell(1, 1).text = "不可删除"
    data = _docx_bytes(document)

    rejected = _run([_op("delete_table_row", key="t0r1c0")], document=data)

    assert rejected.applied == 0
    assert "只能删除空行" in rejected.removals[0].reason


def _placeholder_template() -> bytes:
    """母本：p0 标题 / p1 「品种名称：____」占位 / p2 结束说明。"""
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    placeholder = document.add_paragraph()
    placeholder.add_run("品种名称：")
    placeholder.add_run("____")
    document.add_paragraph("结束说明")
    return _docx_bytes(document)


def _filled_placeholder() -> tuple[bytes, dict[str, Any], dict[str, Any]]:
    """先在占位段写入内容，返回成品字节、位置锚点与对应的写入记录。"""
    template = _placeholder_template()
    position = _outline(template).by_key()["p1"]
    filled = apply_operations(template, _outline(template), {}, [_op("update_text", key="p1", text="阿莫西林")])
    assert filled.ok is True and filled.document is not None
    rows = {"p1": _slot("p1", value="阿莫西林", anchor=position.anchor())}
    return filled.document, position.anchor(), rows


def test_restore_filled_paragraph_returns_placeholder() -> None:
    """还原 = 内容回到母本原样：下划线占位恢复，段落节点保留。"""
    document, anchor, rows = _filled_placeholder()
    assert _paragraphs(document)[1] == "品种名称：阿莫西林"

    run = apply_operations(document, _outline(_placeholder_template()), rows, [_op("restore_position", key="p1")])

    assert run.ok is True
    assert run.document is not None
    assert _paragraphs(run.document) == ["1 数据", "品种名称：____", "结束说明"]
    change = run.slot_changes[0]
    assert change.action == "delete"
    assert change.operation == "restore_position"
    assert change.value is None


def test_restore_removes_multiline_tail_paragraphs() -> None:
    """多行写入会在首段后插段落；还原时只删与写入值一致的残留。"""
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    document.add_paragraph("")
    document.add_paragraph("结束说明")
    template = _docx_bytes(document)
    position = _outline(template).by_key()["p1"]
    filled = apply_operations(
        template, _outline(template), {}, [_op("update_text", key="p1", text="第一行\n第二行")]
    )
    assert filled.ok is True and filled.document is not None
    assert _paragraphs(filled.document) == ["1 数据", "第一行", "第二行", "结束说明"]
    rows = {"p1": _slot("p1", value="第一行\n第二行", anchor=position.anchor())}

    run = apply_operations(filled.document, _outline(template), rows, [_op("restore_position", key="p1")])

    assert run.ok is True
    assert run.document is not None
    assert _paragraphs(run.document) == ["1 数据", "", "结束说明"]


def test_restore_filled_cell_returns_to_original() -> None:
    template = _template()
    position = _outline(template).by_key()["t0r1c1"]
    filled = apply_operations(template, _outline(template), {}, [_op("update_cell", key="t0r1c1", text="92.1%")])
    assert filled.ok is True and filled.document is not None
    rows = {"t0r1c1": _slot("t0r1c1", value="92.1%", anchor=position.anchor())}

    run = apply_operations(filled.document, _outline(template), rows, [_op("restore_position", key="t0r1c1")])

    assert run.ok is True
    assert run.document is not None
    assert open_document(run.document).tables[0].cell(1, 1).text == ""
    assert run.slot_changes[0].action == "delete"


def test_restore_multiline_cell_drops_extra_paragraphs() -> None:
    """多行写入给单元格加过段落；还原要把这些节点删掉，不能留空段撑高行。"""
    template = _template()
    position = _outline(template).by_key()["t0r1c1"]
    filled = apply_operations(
        template, _outline(template), {}, [_op("update_cell", key="t0r1c1", text="第一行\n第二行")]
    )
    assert filled.ok is True and filled.document is not None
    rows = {"t0r1c1": _slot("t0r1c1", value="第一行\n第二行", anchor=position.anchor())}

    run = apply_operations(filled.document, _outline(template), rows, [_op("restore_position", key="t0r1c1")])

    assert run.ok is True
    assert run.document is not None
    cell = open_document(run.document).tables[0].cell(1, 1)
    assert cell.text == ""
    assert len(cell.paragraphs) == 1


def test_update_after_fill_can_locate_again() -> None:
    """下划线占位段写过之后，文本已不是母本原文：二次编辑仍要能定位到同一段。"""
    document, _anchor, rows = _filled_placeholder()

    run = apply_operations(
        document, _outline(_placeholder_template()), rows, [_op("update_text", key="p1", text="阿莫西林胶囊")]
    )

    assert run.ok is True
    assert run.document is not None
    assert _paragraphs(run.document)[1] == "品种名称：阿莫西林胶囊"


def test_restore_without_write_record_is_rejected() -> None:
    run = _run([_op("restore_position", key="p1")])

    assert run.applied == 0
    assert "没有填写记录" in run.removals[0].reason
    assert run.removals[0].restored is False


def test_restore_fixed_paragraph_with_record_is_allowed() -> None:
    """固定内容人工改过之后，同样可以用「还原」回到母本原样。"""
    template = _template()
    position = _outline(template).by_key()["p2"]
    edited = apply_operations(template, _outline(template), {}, [_op("update_text", key="p2", text="人工改过")])
    assert edited.document is not None
    rows = {"p2": _slot("p2", value="人工改过", anchor=position.anchor())}

    run = apply_operations(edited.document, _outline(template), rows, [_op("restore_position", key="p2")])

    assert run.ok is True
    assert run.applied == 1
    assert _paragraphs(run.document or b"")[2] == "本段为固定说明文字"


def test_anchor_unresolved_is_rejected() -> None:
    template = _template()
    outline = _outline(template)

    run = apply_operations(_short_template(), outline, {}, [_op("update_text", key="p4", text="写错位置")])

    assert run.applied == 0
    assert "找不到这一处" in run.removals[0].reason


def test_partial_success_keeps_valid_edits_and_restores_invalid_one() -> None:
    """一处写坏不能拖垮整批：合法修改落盘，非法那处回到母本原样。"""
    run = _run(
        [
            _op("update_text", key="p1", text="合法修改"),
            _op("update_text", key="p2", text=""),
        ]
    )

    assert run.ok is True
    assert run.document is not None
    assert run.applied == 1
    assert len(run.removals) == 1
    assert run.removals[0].key == "p2"
    assert run.removals[0].restored is True
    paragraphs = _paragraphs(run.document)
    assert paragraphs[1] == "合法修改"
    assert paragraphs[2] == "本段为固定说明文字"


def test_failed_update_restores_previous_value_to_template() -> None:
    """已写过内容的位置再改坏：必须回到母本原样，并软删旧写入记录，避免重渲写回。"""
    document, anchor, rows = _filled_placeholder()

    run = apply_operations(
        document,
        _outline(_placeholder_template()),
        rows,
        [_op("update_text", key="p1", text="")],
    )

    assert run.applied == 0
    assert run.document is not None
    assert _paragraphs(run.document)[1] == "品种名称：____"
    assert run.removals[0].restored is True
    assert any(change.key == "p1" and change.action == "delete" for change in run.slot_changes)


@pytest.mark.parametrize(
    ("key", "op", "reason"),
    [
        ("p99", "update_text", "定位不到这个位置"),
        ("t9r1c1", "update_cell", "定位不到这个表格单元格"),
        ("ap9", "delete_paragraph", "只能删除"),
        ("p1", "insert_paragraph", "要插入的内容不能为空"),
    ],
)
def test_invalid_operations_are_rejected(key: str, op: str, reason: str) -> None:
    request = _op(op, key=key, text=None if op == "delete_paragraph" else "")
    run = _run([request])

    assert run.applied == 0
    assert reason in run.removals[0].reason
