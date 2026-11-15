"""出稿回放测试：覆盖写入、追加段落/表格行，以及「格式必须来自母本」。

验收第 3 条要求「段落样式集合 ⊆ 母本样式集合、表格边框/行高与母本一致」。这里不靠肉眼
比对 docx，而是直接断言：样式表条目数不变、新段落的 pPr/rPr 是深拷贝、新行带 tcPr。
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from docx import Document
from docx.document import Document as DocxDocument
from docx.shared import Pt

from app.modules.research.report_gen.render import (
    KIND_APPEND_PARAGRAPH,
    KIND_APPEND_TABLE_ROWS,
    KIND_PARAGRAPH,
    KIND_REFERENCES,
    KIND_TABLE_CELL,
    SlotFill,
    render_document,
)
from app.modules.research.report_gen.structure import fingerprint


def _docx(document: DocxDocument) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _paragraph_anchor(index: int, text: str) -> dict[str, Any]:
    return {"kind": KIND_PARAGRAPH, "index": index, "text": text, "fingerprint": fingerprint(text)}


def _cell_anchor(text: str, row: int, col: int) -> dict[str, Any]:
    return {
        "kind": KIND_TABLE_CELL,
        "table_index": 0,
        "row": row,
        "col": col,
        "para_index": 0,
        "text": text,
        "fingerprint": fingerprint(text),
    }


def _template() -> bytes:
    document = Document()
    paragraph = document.add_paragraph()
    bold = paragraph.add_run("品种名称：")
    bold.bold = True
    paragraph.add_run("____")

    document.add_paragraph("本段是固定说明")
    document.add_paragraph("3.1 路线一", style="Heading 2")
    content = document.add_paragraph("路线一的内容")
    content.paragraph_format.first_line_indent = Pt(21)

    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "结论"
    table.cell(1, 0).text = "纯度"
    table.cell(1, 1).text = ""
    return _docx(document)


def test_placeholder_fill_keeps_label_and_bold() -> None:
    output = render_document(
        _template(),
        [
            SlotFill(
                slot_key="p0",
                label="正文第1段",
                anchor=_paragraph_anchor(0, "品种名称：____"),
                value="阿莫西林",
                state="filled",
            )
        ],
    )
    document = Document(BytesIO(output.document))
    paragraph = document.paragraphs[0]
    assert paragraph.text == "品种名称：阿莫西林"
    assert paragraph.runs[0].bold is True
    assert output.filled == 1


def test_value_repeating_label_is_deduped() -> None:
    """模型把「品种名称：」一起写进 text 时，不能渲染成「品种名称：品种名称：X」。"""
    output = render_document(
        _template(),
        [
            SlotFill(
                slot_key="p0",
                label="正文第1段",
                anchor=_paragraph_anchor(0, "品种名称：____"),
                value="品种名称：阿莫西林",
                state="filled",
            )
        ],
    )
    document = Document(BytesIO(output.document))
    assert document.paragraphs[0].text == "品种名称：阿莫西林"


def test_caption_placeholder_replaces_only_xxx() -> None:
    document = Document()
    document.add_paragraph("表2 XXX主要物料供应信息")

    output = render_document(
        _docx(document),
        [
            SlotFill(
                slot_key="p0",
                label="正文第1段",
                anchor=_paragraph_anchor(0, "表2 XXX主要物料供应信息"),
                value="阿莫西林",
                state="filled",
            )
        ],
    )
    assert Document(BytesIO(output.document)).paragraphs[0].text == "表2 阿莫西林主要物料供应信息"


def test_label_paragraph_appends_without_overwriting_label() -> None:
    """「制剂/规格：」这类标签段：只接值，标签与格式保留。"""
    document = Document()
    label = document.add_paragraph()
    bold = label.add_run("制剂/规格：")
    bold.bold = True

    output = render_document(
        _docx(document),
        [
            SlotFill(
                slot_key="p0",
                label="正文第1段",
                anchor={**_paragraph_anchor(0, "制剂/规格："), "append": True},
                value="片剂 10mg",
                state="filled",
            )
        ],
    )
    rendered = Document(BytesIO(output.document)).paragraphs[0]
    assert rendered.text == "制剂/规格：片剂 10mg"
    assert rendered.runs[0].bold is True
    assert output.filled == 1


def test_label_append_dedupes_value_that_repeats_label() -> None:
    document = Document()
    document.add_paragraph("制剂/规格：")

    output = render_document(
        _docx(document),
        [
            SlotFill(
                slot_key="p0",
                label="正文第1段",
                anchor={**_paragraph_anchor(0, "制剂/规格："), "append": True},
                value="制剂/规格：片剂 10mg",
                state="filled",
            )
        ],
    )
    assert Document(BytesIO(output.document)).paragraphs[0].text == "制剂/规格：片剂 10mg"


def test_multiline_value_creates_sibling_paragraphs() -> None:
    output = render_document(
        _template(),
        [
            SlotFill(
                slot_key="p1",
                label="正文第2段",
                anchor=_paragraph_anchor(1, "本段是固定说明"),
                value="第一行\n第二行",
                state="filled",
            )
        ],
    )
    document = Document(BytesIO(output.document))
    texts = [item.text for item in document.paragraphs]
    assert texts[1] == "第一行"
    assert texts[2] == "第二行"


def test_cell_write_and_fingerprint_fallback() -> None:
    # 行列故意写错（落到「项目/结论」那一行），但文本锚点指向「纯度」
    wrong_position = {
        "kind": KIND_TABLE_CELL,
        "table_index": 0,
        "row": 0,
        "col": 1,
        "para_index": 0,
        "text": "结论",
        "fingerprint": fingerprint("结论"),
    }
    output = render_document(
        _template(),
        [
            SlotFill(
                slot_key="t0r1c1",
                label="表1第2行第2列",
                anchor=_cell_anchor("", 1, 1),
                value="99.2%",
                state="filled",
            ),
            SlotFill(slot_key="t0r0c1", label="表1第1行第2列", anchor=wrong_position, value="结论替换", state="filled"),
        ],
    )
    document = Document(BytesIO(output.document))
    assert document.tables[0].cell(1, 1).text == "99.2%"
    assert document.tables[0].cell(0, 1).text == "结论替换"


def test_append_paragraph_keeps_source_style_and_indent() -> None:
    template = _template()
    styles_before = len(Document(BytesIO(template)).styles)
    output = render_document(
        template,
        [
            SlotFill(
                slot_key="ap1",
                label="追加段落1",
                anchor={
                    "kind": KIND_APPEND_PARAGRAPH,
                    "after": "p3",
                    "clone_from": 2,
                    "seq": 1,
                    "location": "文末第1段",
                },
                value="3.2 路线二",
                state="filled",
            ),
            SlotFill(
                slot_key="ap2",
                label="追加段落2",
                anchor={
                    "kind": KIND_APPEND_PARAGRAPH,
                    "after": "ap1",
                    "clone_from": 3,
                    "seq": 2,
                    "location": "文末第2段",
                },
                value="路线二的内容",
                state="filled",
            ),
        ],
    )
    document = Document(BytesIO(output.document))
    texts = [item.text for item in document.paragraphs]
    heading_index = texts.index("3.2 路线二")
    body_index = texts.index("路线二的内容")
    assert heading_index + 1 == body_index
    # 标题克隆自 p3（Heading 2），正文克隆自 p4（带首行缩进）
    heading_style = document.paragraphs[heading_index].style
    assert heading_style is not None and heading_style.name == "Heading 2"
    assert document.paragraphs[body_index].paragraph_format.first_line_indent == Pt(21)
    # 没有新增样式
    assert len(document.styles) == styles_before
    assert output.unresolved == []


def test_append_table_rows_deep_copies_row_format() -> None:
    output = render_document(
        _template(),
        [
            SlotFill(
                slot_key="at1",
                label="表1追加行1",
                anchor={
                    "kind": KIND_APPEND_TABLE_ROWS,
                    "table_index": 0,
                    "clone_from_row": 1,
                    "seq": 1,
                    "rows": [{"cells": ["杂质", "0.1%"], "source_ids": ["s1"]}],
                },
                value="杂质 | 0.1%",
                state="filled",
            )
        ],
    )
    document = Document(BytesIO(output.document))
    table = document.tables[0]
    assert len(table.rows) == 3
    assert table.cell(2, 0).text == "杂质"
    assert table.cell(2, 1).text == "0.1%"
    # 深拷贝母本行：tcPr（列宽等）必须还在
    assert table.rows[2]._tr.tc_lst[0].tcPr is not None


def test_append_table_rows_without_clone_row_uses_last_row_format() -> None:
    """clone_from_row 缺省时克隆最后一行；退回 add_row() 会丢 tcPr（边框/列宽）。"""
    output = render_document(
        _template(),
        [
            SlotFill(
                slot_key="at1",
                label="表1追加行1",
                anchor={
                    "kind": KIND_APPEND_TABLE_ROWS,
                    "table_index": 0,
                    "seq": 1,
                    "rows": [{"cells": ["杂质", "0.1%"], "source_ids": ["s1"]}],
                },
                value="杂质 | 0.1%",
                state="filled",
            )
        ],
    )
    document = Document(BytesIO(output.document))
    table = document.tables[0]
    assert len(table.rows) == 3
    assert table.cell(2, 0).text == "杂质"
    for col in range(2):
        current = table.rows[2].cells[col]._tc.tcPr
        above = table.rows[1].cells[col]._tc.tcPr
        assert current is not None and above is not None
        assert current.xml == above.xml


def test_references_are_not_written_into_document() -> None:
    """参考资料只在详情页右栏展示：ref 记录不能往成稿里加标题或条目。"""
    template = _template()
    styles_before = len(Document(BytesIO(template)).styles)
    before = [item.text for item in Document(BytesIO(template)).paragraphs]

    output = render_document(
        template,
        [
            SlotFill(
                slot_key="p1",
                label="正文第2段",
                anchor=_paragraph_anchor(1, ""),
                value="6 批实验数据汇总",
                state="filled",
            ),
            SlotFill(
                slot_key="ref",
                label="参考资料",
                anchor={
                    "kind": KIND_REFERENCES,
                    "entries": ["[1] 小试报告.pdf（用于：正文第2段）", "[2] 工艺规程.docx（用于：表1第2行第2列）"],
                },
                value="[1] 小试报告.pdf（用于：正文第2段）\n[2] 工艺规程.docx（用于：表1第2行第2列）",
                state="filled",
            ),
        ],
    )

    document = Document(BytesIO(output.document))
    texts = [item.text for item in document.paragraphs]
    assert "引用源" not in texts and "参考资料" not in texts
    assert not any(text.startswith("[1] 小试报告.pdf") for text in texts)
    # 只有正文写入生效，段落数与样式表都不变
    assert len(texts) == len(before)
    assert texts[1] == "6 批实验数据汇总"
    assert len(document.styles) == styles_before


def test_unresolved_when_anchor_missing() -> None:
    output = render_document(
        _template(),
        [
            SlotFill(
                slot_key="p99",
                label="正文第100段",
                anchor={"kind": KIND_PARAGRAPH, "index": 99, "text": "不存在", "fingerprint": fingerprint("不存在")},
                value="x",
                state="filled",
            )
        ],
    )
    assert output.unresolved == ["p99"]
    assert output.filled == 0


def test_legacy_gap_row_still_renders_pending_text() -> None:
    """老任务里 state=gap 的行重渲时仍写「待补充」，不影响历史成品。"""
    output = render_document(
        _template(),
        [
            SlotFill(
                slot_key="p1",
                label="正文第2段",
                anchor=_paragraph_anchor(1, "本段是固定说明"),
                value=None,
                state="gap",
                owner_hint="质量部",
            )
        ],
    )
    document = Document(BytesIO(output.document))
    assert document.paragraphs[1].text == "待补充：质量部"
    assert output.gaps == 1
