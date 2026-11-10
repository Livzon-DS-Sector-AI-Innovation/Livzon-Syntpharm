"""AI 报告成稿回写与母本结构解析的单元测试。

用 python-docx 现造母本，覆盖：段落内多 run、单元格多段落、锚点漂移、
缺口占位与未定位降级。全流程不碰数据库与外部服务。
"""

from __future__ import annotations

from io import BytesIO

import pytest
from docx import Document

from app.modules.research.report_gen.render import SlotFill, render_document
from app.modules.research.report_gen.structure import (
    build_candidates,
    cell_refs,
    fingerprint,
    open_document,
    paragraph_refs,
)


def _template_bytes() -> bytes:
    """造一份带「多 run 段落 + 表格单元格」的假母本。"""
    document = Document()
    paragraph = document.add_paragraph()
    bold_run = paragraph.add_run("品种名称：")
    bold_run.bold = True
    paragraph.add_run("____")

    document.add_paragraph("以下为结论：")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "内容"
    table.cell(1, 0).text = "结论"
    table.cell(1, 1).text = ""

    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _paragraph_anchor(index: int, text: str) -> dict[str, object]:
    return {"kind": "paragraph", "index": index, "text": text, "fingerprint": fingerprint(text)}


def _cell_anchor(row: int, col: int) -> dict[str, object]:
    return {"kind": "table_cell", "table_index": 0, "row": row, "col": col, "para_index": 0}


def test_paragraph_multi_run_keeps_label_and_styles() -> None:
    """只替换填空位：标签 run 与加粗格式保留，值落在原占位 run 里。"""
    output = render_document(
        _template_bytes(),
        [
            SlotFill(
                slot_key="drug_name",
                label="品种名称",
                anchor=_paragraph_anchor(0, "品种名称：____"),
                value="化合物A",
                state="filled",
            )
        ],
    )

    document = open_document(output.document)
    paragraph = document.paragraphs[0]
    assert paragraph.text == "品种名称：化合物A"
    assert len(paragraph.runs) == 2
    assert paragraph.runs[0].text == "品种名称："
    assert paragraph.runs[0].bold is True
    assert paragraph.runs[1].text == "化合物A"
    assert output.filled == 1
    assert output.unresolved == []


def test_blank_in_middle_of_multi_run_paragraph_keeps_suffix() -> None:
    """占位在段中间时，前后文字都保留（回归：整段替换会吃掉标签与后缀）。"""
    document = Document()
    line = document.add_paragraph()
    line.add_run("报告标题：").bold = True
    line.add_run("____")
    line.add_run("（此行由多个 run 组成）")
    buffer = BytesIO()
    document.save(buffer)

    output = render_document(
        buffer.getvalue(),
        [
            SlotFill(
                slot_key="report_title",
                label="报告标题",
                anchor=_paragraph_anchor(0, "报告标题：____（此行由多个 run 组成）"),
                value="化合物A技术调研报告",
                state="filled",
            )
        ],
    )

    paragraph = open_document(output.document).paragraphs[0]
    assert paragraph.text == "报告标题：化合物A技术调研报告（此行由多个 run 组成）"
    assert len(paragraph.runs) == 3


def test_multiline_value_inserts_new_paragraph_with_style() -> None:
    """多行值按段落拆开，新段落继承占位 run 的样式（这里断言加粗被复制）。"""
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("结论：")
    blank = paragraph.add_run("____")
    blank.bold = True
    buffer = BytesIO()
    document.save(buffer)

    output = render_document(
        buffer.getvalue(),
        [
            SlotFill(
                slot_key="conclusion",
                label="结论",
                anchor=_paragraph_anchor(0, "结论：____"),
                value="第一行结论\n第二行结论",
                state="filled",
            )
        ],
    )

    result = open_document(output.document)
    assert result.paragraphs[0].text == "结论：第一行结论"
    assert result.paragraphs[1].text == "第二行结论"
    assert result.paragraphs[1].runs[0].bold is True


def test_table_cell_written_and_gap_uses_placeholder() -> None:
    """表格单元格可写入；无资料支撑的槽位写「待补充：责任方」。"""
    output = render_document(
        _template_bytes(),
        [
            SlotFill(slot_key="conclusion", label="结论", anchor=_cell_anchor(1, 1), value="工艺稳定", state="filled"),
            SlotFill(
                slot_key="stability",
                label="稳定性",
                anchor=_paragraph_anchor(1, "以下为结论："),
                value="",
                state="gap",
                owner_hint="分析部",
            ),
        ],
    )

    document = open_document(output.document)
    assert document.tables[0].cell(1, 1).text == "工艺稳定"
    assert document.paragraphs[1].text == "待补充：分析部"
    assert output.filled == 1
    assert output.gaps == 1


def test_anchor_drift_falls_back_to_fingerprint() -> None:
    """索引失效时用原文指纹兜底定位，内容仍写到正确段落。"""
    output = render_document(
        _template_bytes(),
        [
            SlotFill(
                slot_key="drug_name",
                label="品种名称",
                # 索指引到不存在的第 9 段，只能靠指纹找到第 0 段
                anchor={
                    "kind": "paragraph",
                    "index": 9,
                    "text": "品种名称：____",
                    "fingerprint": fingerprint("品种名称：____"),
                },
                value="化合物B",
                state="filled",
            )
        ],
    )

    document = open_document(output.document)
    assert document.paragraphs[0].text == "品种名称：化合物B"
    assert output.unresolved == []


def test_unresolved_anchor_is_recorded_not_fatal() -> None:
    """锚点彻底失效：不中断整体生成，记入 unresolved 并在对照表标注。"""
    output = render_document(
        _template_bytes(),
        [
            SlotFill(
                slot_key="ghost",
                label="失效槽位",
                anchor={
                    "kind": "paragraph",
                    "index": 99,
                    "text": "模板里没有这句",
                    "fingerprint": fingerprint("模板里没有这句"),
                },
                value="随便",
                state="filled",
            )
        ],
    )

    assert output.unresolved == ["ghost"]
    assert "锚点未定位" in output.comparison_markdown
    # 母本仍能正常保存
    assert len(open_document(output.document).paragraphs) >= 2


def test_build_candidates_covers_paragraph_and_table_cell() -> None:
    """结构解析候选同时收口正文段落与表格单元格，并带稳定指纹。"""
    document = open_document(_template_bytes())
    paragraphs = paragraph_refs(document)
    cells = cell_refs(document)
    assert paragraphs[0].text == "品种名称：____"
    assert any(cell.row == 1 and cell.col == 1 for cell in cells)

    candidates = build_candidates(paragraphs, cells)
    kinds = {candidate["kind"] for candidate in candidates}
    assert kinds == {"paragraph", "table_cell"}
    for candidate in candidates:
        assert candidate["anchor"]["fingerprint"] == fingerprint(
            (candidate["text"] or "").strip()
        )


def test_cell_refs_keeps_every_distinct_cell_of_merged_table() -> None:
    """多行多列表里每个单元格都要收；真合并单元格的重复引用只取首现。

    回归点：去重标识曾用 ``id(cell._tc)``，底层节点代理被回收后 id 被复用，
    正常单元格会被当成「已出现」跳过（2x2 表少一格、空单元格首当其冲）。
    """
    document = Document()
    table = document.add_table(rows=3, cols=3)
    for row in range(3):
        for col in range(3):
            table.cell(row, col).text = f"r{row}c{col}"
    # 真横向合并：(0,0) 与 (0,1) 变成同一个 w:tc，(0,1) 必须被去重
    table.cell(0, 0).merge(table.cell(0, 1))

    refs = cell_refs(document)
    positions = {(ref.row, ref.col) for ref in refs}

    assert positions == {(row, col) for row in range(3) for col in range(3)} - {(0, 1)}
    # 合并后的单元格两个原段落都保留，引用次数与段落数一致
    assert sum(1 for ref in refs if (ref.row, ref.col) == (0, 0)) == 2
    assert any(ref.row == 1 and ref.col == 1 and ref.text == "r1c1" for ref in refs)


@pytest.mark.parametrize("text", ["", " ", "品种名称：____", "品种名称：___X"])
def test_fingerprint_is_stable_and_text_sensitive(text: str) -> None:
    assert fingerprint(text) == fingerprint(text)
    if text.strip() and text.strip() != "品种名称：____":
        assert fingerprint(text) != fingerprint("品种名称：____")
