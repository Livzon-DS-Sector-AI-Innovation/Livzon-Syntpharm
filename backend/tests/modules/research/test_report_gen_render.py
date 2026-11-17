"""出稿回放测试：覆盖写入、追加段落/表格行，以及「格式必须来自母本」。

验收第 3 条要求「段落样式集合 ⊆ 母本样式集合、表格边框/行高与母本一致」。这里不靠肉眼
比对 docx，而是直接断言：样式表条目数不变、新段落的 pPr/rPr 是深拷贝、新行带 tcPr。
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Pt

from app.modules.research.report_gen.outline import paragraph_heading_level
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


# ----------------------------------------------------------------------
# 动态子标题与目录：母本只有路线1-4，资料里有路线5、路线6
# ----------------------------------------------------------------------
def _add_toc_entry(document: DocxDocument, title: str, page: str, style: str) -> Any:
    paragraph = document.add_paragraph(style=style)
    paragraph.add_run(title)
    tab_run = paragraph.add_run()
    tab_run._r.append(OxmlElement("w:tab"))
    paragraph.add_run(page)
    return paragraph


def _toc_template(level_range: str = "1-2") -> bytes:
    """带真实 TOC 域的母本：目录缓存 4.4 条目 + 一级标题 + 路线4 子标题。"""
    document = Document()
    existing = {style.name for style in document.styles}
    for name in ("toc 1", "toc 2"):
        if name not in existing:
            document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)

    document.add_paragraph("目录", style="Heading 1")
    field = document.add_paragraph()
    begin_run = field.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin_run._r.append(begin)
    instr_run = field.add_run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f' TOC \\o "{level_range}" \\h \\z \\u '
    instr_run._r.append(instr)
    separator_run = field.add_run()
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    separator_run._r.append(separate)

    _add_toc_entry(document, "4. 工艺路线的调研", "4", "toc 1")
    _add_toc_entry(document, "4.4. 路线4", "5", "toc 2")
    _add_toc_entry(document, "4.5. 综合选择和说明", "5", "toc 2")
    reference = _add_toc_entry(document, "5. 成本估算和分析", "6", "toc 1")
    end_run = reference.add_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run._r.append(end)

    document.add_paragraph("4 工艺路线的调研", style="Heading 1")
    document.add_paragraph("路线4", style="Heading 2")
    document.add_paragraph("路线4的内容")
    return _docx(document)


def _style_name(paragraph: Any) -> str:
    style = paragraph.style
    return (style.name if style is not None else "") or ""


def _subsection_fill(key: str, title: str, *, after: str, seq: int) -> SlotFill:
    """一条「新增子标题 + 正文」写入记录；clone_from 7/8 是母本的子标题与正文段。"""
    return SlotFill(
        slot_key=key,
        label=f"新增子标题{seq}：{title}",
        anchor={
            "kind": KIND_APPEND_PARAGRAPH,
            "after": after,
            "clone_from": 7,
            "heading": 2,
            "title": title,
            "paragraphs": [{"text": f"{title}的内容", "clone_from": 8}],
            "seq": seq,
            "location": f"新增子章节：{title}",
        },
        value=f"{title}\n{title}的内容",
        state="filled",
    )


def test_append_subsection_updates_toc_and_marks_fields() -> None:
    template = _toc_template()
    styles_before = len(Document(BytesIO(template)).styles)

    output = render_document(
        template,
        [
            _subsection_fill("as1", "路线5", after="p8", seq=1),
            _subsection_fill("as2", "路线6", after="as1", seq=2),
        ],
    )

    assert output.unresolved == []
    document = Document(BytesIO(output.document))
    texts = [item.text for item in document.paragraphs]
    heading5 = texts.index("路线5")
    heading6 = texts.index("路线6")
    assert heading5 < heading6
    assert _style_name(document.paragraphs[heading5]) == "Heading 2"
    # 正文跟在各自子标题之后，而不是挤在标题前面
    assert texts[heading5 + 1] == "路线5的内容"
    assert texts[heading6 + 1] == "路线6的内容"

    toc_texts = [item.text for item in document.paragraphs if _style_name(item).lower().startswith("toc")]
    route5_entry = next(index for index, text in enumerate(toc_texts) if text.startswith("4.5. 路线5"))
    route6_entry = next(index for index, text in enumerate(toc_texts) if text.startswith("4.6. 路线6"))
    summary_entry = next(index for index, text in enumerate(toc_texts) if text.startswith("4.7. 综合选择和说明"))
    # 新条目仍在目录域内（下一章之前），没有落到目录外面
    chapter5_entry = next(index for index, text in enumerate(toc_texts) if text.startswith("5. 成本估算"))
    assert route5_entry < route6_entry < summary_entry < chapter5_entry
    # 页码先沿用参照条目，Word 打开时按实际版式重算
    assert toc_texts[route5_entry].endswith("5")

    assert 'w:dirty="true"' in document.element.xml
    assert "updateFields" in document.settings.element.xml
    assert len(document.styles) == styles_before


def test_append_subsection_renumbers_toc_after_insert() -> None:
    """只插一条路线5：目录应为 4.4 路线4 → 4.5 路线5 → 4.6 综合选择和说明。"""
    output = render_document(_toc_template(), [_subsection_fill("as1", "路线5", after="p8", seq=1)])

    document = Document(BytesIO(output.document))
    toc_texts = [item.text for item in document.paragraphs if _style_name(item).lower().startswith("toc")]
    assert any(text.startswith("4.5. 路线5") for text in toc_texts)
    assert any(text.startswith("4.6. 综合选择和说明") for text in toc_texts)
    assert not any(text.startswith("4.5. 综合选择和说明") for text in toc_texts)


def _outline_style(document: DocxDocument, name: str, level: int) -> None:
    """自定义标题样式：只有大纲级别，没有 Heading N 这种样式名。"""
    style = document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    node = OxmlElement("w:outlineLvl")
    node.set(qn("w:val"), str(level - 1))
    style.element.get_or_add_pPr().append(node)


def _toc_template_chinese() -> bytes:
    """中文序号 + 自定义标题样式：四、路线4 / 五、综合选择和说明。"""
    document = Document()
    existing = {style.name for style in document.styles}
    for name in ("toc 1", "toc 2"):
        if name not in existing:
            document.styles.add_style(name, WD_STYLE_TYPE.PARAGRAPH)
    _outline_style(document, "章节标题", 1)
    _outline_style(document, "子标题", 2)

    document.add_paragraph("目录", style="章节标题")
    field = document.add_paragraph()
    begin_run = field.add_run()
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    begin_run._r.append(begin)
    instr_run = field.add_run()
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = ' TOC \\o "1-2" \\h \\z \\u '
    instr_run._r.append(instr)
    separator_run = field.add_run()
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    separator_run._r.append(separate)

    _add_toc_entry(document, "四、路线4", "5", "toc 2")
    reference = _add_toc_entry(document, "五、综合选择和说明", "5", "toc 2")
    end_run = reference.add_run()
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    end_run._r.append(end)

    document.add_paragraph("四 工艺路线", style="章节标题")
    document.add_paragraph("路线4", style="子标题")
    document.add_paragraph("路线4的内容")
    return _docx(document)


def test_append_subsection_handles_chinese_numbers_and_custom_heading_styles() -> None:
    """换一个模板、换一种编号写法、换一套标题样式，行为必须一致。"""
    output = render_document(
        _toc_template_chinese(),
        [
            SlotFill(
                slot_key="as1",
                label="新增子标题1：路线5",
                anchor={
                    "kind": KIND_APPEND_PARAGRAPH,
                    "after": "p6",
                    "clone_from": 5,
                    "heading": 2,
                    "title": "路线5",
                    "paragraphs": [{"text": "路线5的内容", "clone_from": 6}],
                    "seq": 1,
                    "location": "新增子章节：路线5",
                },
                value="路线5\n路线5的内容",
                state="filled",
            )
        ],
    )

    document = Document(BytesIO(output.document))
    toc_texts = [item.text for item in document.paragraphs if _style_name(item).lower().startswith("toc")]
    assert any(text.startswith("五、路线5") for text in toc_texts)
    assert any(text.startswith("六、综合选择和说明") for text in toc_texts)
    assert not any(text.startswith("五、综合选择和说明") for text in toc_texts)
    new_heading = next(item for item in document.paragraphs if item.text == "路线5")
    assert paragraph_heading_level(new_heading) == 2


def test_append_subsection_skips_toc_entry_beyond_toc_levels() -> None:
    """目录只收 1-1 级时，Heading 2 不进缓存条目，但域更新标记照打。"""
    template = _toc_template(level_range="1-1")

    output = render_document(template, [_subsection_fill("as1", "路线5", after="p8", seq=1)])

    document = Document(BytesIO(output.document))
    toc_texts = [item.text for item in document.paragraphs if _style_name(item).lower().startswith("toc")]
    assert not any("路线5" in text for text in toc_texts)
    # 标题本身仍然进正文
    assert "路线5" in [item.text for item in document.paragraphs]
    assert "updateFields" in document.settings.element.xml


def test_append_subsection_without_toc_only_inserts_heading() -> None:
    """没有目录域的模板不凭空造目录：只插标题与正文，settings 不写 updateFields。"""
    template = _template()
    output = render_document(
        template,
        [
            SlotFill(
                slot_key="as1",
                label="新增子标题1：路线5",
                anchor={
                    "kind": KIND_APPEND_PARAGRAPH,
                    "after": "p3",
                    "clone_from": 2,
                    "heading": 2,
                    "title": "路线5",
                    "paragraphs": [{"text": "路线5的内容", "clone_from": 3}],
                    "seq": 1,
                    "location": "新增子章节：路线5",
                },
                value="路线5\n路线5的内容",
                state="filled",
            )
        ],
    )

    document = Document(BytesIO(output.document))
    texts = [item.text for item in document.paragraphs]
    assert texts[texts.index("路线5") + 1] == "路线5的内容"
    assert "updateFields" not in document.settings.element.xml
