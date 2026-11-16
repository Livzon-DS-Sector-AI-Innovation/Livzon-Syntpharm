"""母本可写位置判定与章节树的单元测试。

判定是「工具能写哪」的唯一真源：这里把负例（标题段、固定文字段、签字区、目录）逐条钉住，
一旦有人放宽条件，验收第 7 条（负例被拒）会直接红。
"""

from __future__ import annotations

from io import BytesIO

from docx import Document
from docx.document import Document as DocxDocument
from docx.enum.style import WD_STYLE_TYPE

from app.modules.research.report_gen.outline import (
    build_outline,
    has_blank,
    heading_level,
    is_fixed_title,
    judge_text,
)
from app.modules.research.report_gen.structure import open_document


def _docx(document: DocxDocument) -> bytes:
    buffer = BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _template() -> DocxDocument:
    document = Document()
    document.add_paragraph("1 项目概况", style="Heading 1")
    document.add_paragraph("")  # 0 可写：空段
    document.add_paragraph("本段为固定说明文字，不允许改写")
    placeholder = document.add_paragraph()
    placeholder.add_run("品种名称：")
    placeholder.add_run("____")
    document.add_paragraph("2 研究路线", style="Heading 1")
    document.add_paragraph("2.1 路线一", style="Heading 2")
    document.add_paragraph("")  # 可写：路线内容
    document.add_paragraph("附件：签字页", style="Heading 1")
    document.add_paragraph("")  # 签字区，不可写
    return document


def test_writable_and_rejected_positions() -> None:
    outline = build_outline(open_document(_docx(_template())))
    positions = outline.by_key()

    # 空段可写
    assert positions["p1"].writable is True
    # 固定文字段拒绝
    assert positions["p2"].writable is False
    assert "完整内容" in (positions["p2"].reason or "")
    # 下划线占位段可写
    assert positions["p3"].writable is True
    # 标题段拒绝
    assert positions["p0"].writable is False
    assert "标题" in (positions["p0"].reason or "")
    # 签字区空段拒绝（p7 是签字页标题，p8 是它下面的空行）
    assert positions["p7"].writable is False
    assert positions["p8"].writable is False
    assert "签字" in (positions["p8"].reason or "")

    assert outline.writable_total == 3
    assert outline.paragraph_count == 9


def test_section_brief_counts_only_writable() -> None:
    outline = build_outline(open_document(_docx(_template())))
    brief = {item["section"]: item["writable"] for item in outline.section_brief()}
    assert brief["1 项目概况"] == 2
    # 归属按最近的标题算：路线一这个二级标题下的空段单独成组
    assert brief["2.1 路线一"] == 1
    # 签字页整章禁写，不该出现在总览里
    assert "附件：签字页" not in brief


def test_table_cells_are_positions_and_signature_table_is_rejected() -> None:
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    table = document.add_table(rows=2, cols=2)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).text = "内容"
    table.cell(1, 0).text = "结论"
    outline = build_outline(open_document(_docx(document)))

    header = outline.by_key()["t0r0c1"]
    assert header.writable is False  # 表头已有文字
    # 空单元格可写，并且带表头提示：行标题（结论）进 context，列标题（内容）单独给 column_hint
    body_cell = outline.by_key()["t0r1c1"]
    assert body_cell.writable is True
    assert body_cell.context == "结论"
    assert body_cell.column_hint == "内容"
    assert body_cell.label == "表1 · 结论 · 内容"

    document2 = Document()
    document2.add_paragraph("签字审批", style="Heading 1")
    document2.add_table(rows=1, cols=1)
    outline2 = build_outline(open_document(_docx(document2)))
    assert outline2.by_key()["t0r0c0"].writable is False


def test_judge_text_rules() -> None:
    assert judge_text("", style="Normal", fixed_section=None) == (True, None, False)
    assert judge_text("品种：＿＿＿＿", style="Normal", fixed_section=None)[0] is True
    writable, reason, append = judge_text("品种名称：", style="Normal", fixed_section=None)
    assert writable is True and append is True and reason is None
    writable, reason, _append = judge_text("固定内容", style="Normal", fixed_section=None)
    assert writable is False and reason
    writable, reason, _append = judge_text("", style="Normal", fixed_section="附件：签字页")
    assert writable is False and "签字" in (reason or "")
    assert judge_text("", style="Heading 3", fixed_section=None)[0] is False
    assert judge_text("", style="TOC 1", fixed_section=None)[0] is False


def test_toc_locks_entries_not_following_body() -> None:
    """目录只锁标题和 toc 条目；紧跟其后的「品种简介」正文不能被整段锁死。"""
    document = Document()
    document.styles.add_style("TOC 1", WD_STYLE_TYPE.PARAGRAPH)
    document.add_paragraph("目录", style="Heading 6")
    document.add_paragraph("1 综合信息\t1", style="TOC 1")
    document.add_paragraph("综合信息")
    document.add_paragraph("")  # 正文空段：可写
    document.add_paragraph("品种简介")
    document.add_paragraph("制剂/规格：")  # 标签段：可写并追加
    document.add_paragraph("本段是固定说明文字")

    outline = build_outline(open_document(_docx(document)))
    positions = outline.by_key()

    assert positions["p0"].writable is False
    assert positions["p1"].writable is False
    assert positions["p3"].writable is True
    assert positions["p4"].writable is False
    assert positions["p5"].writable is True
    assert positions["p5"].append is True
    assert positions["p6"].writable is False


def test_toc_style_is_locked_without_fixed_section() -> None:
    """目录条目即使没有被 section 标记锁住，toc 样式本身也不能写。"""
    document = Document()
    document.styles.add_style("TOC 1", WD_STYLE_TYPE.PARAGRAPH)
    document.add_paragraph("1 综合信息\t3", style="TOC 1")
    outline = build_outline(open_document(_docx(document)))
    assert outline.by_key()["p0"].writable is False


def test_fixed_title_whitelist_hits() -> None:
    """固定章节只认白名单标题：真目录/附件/签字审批整章禁写。"""
    for title in (
        "目录",
        "目 录",
        "6.1 目录：",
        "目录（自动生成）",
        "附件",
        "附件清单",
        "附件1",
        "附表二",
        "附录A",
        "修订记录",
        "变更历史",
        "版本历史",
        "签字审批",
        "附件：签字页",
        "编制/审核/批准",
        "编制审核批准",
    ):
        assert is_fixed_title(title) is True, title


def test_fixed_title_whitelist_avoids_false_positive() -> None:
    """正文标题带关键词不算固定章节：产品目录、数据审核、工艺编制说明都不能整章锁死。"""
    for title in (
        "产品目录",
        "物料目录",
        "数据审核",
        "审核流程",
        "工艺编制说明",
        "稳定性试验方案",
        "附件1 稳定性试验方案",
        "1 项目概况",
        "",
    ):
        assert is_fixed_title(title) is False, title


def test_style_and_blank_helpers() -> None:
    assert heading_level("Heading 2") == 2
    assert heading_level("标题 1") == 1
    assert heading_level("Title") == 1
    assert heading_level("Normal") is None
    assert has_blank("____") is True
    assert has_blank("＿＿") is True
    assert has_blank("_") is False
    # 模板题注里的 XXX/XXXX 也是占位；两个 X 太容易是正常缩写，不当占位
    assert has_blank("表2 XXX主要物料供应信息") is True
    assert has_blank("表4 XXXX杂质谱") is True
    assert has_blank("XX 项目") is False


def test_merged_header_gives_row_and_column_semantics() -> None:
    """合并表头下也要给出「这一行这一列是什么」，而不是占位符或别的格子的字。"""
    document = Document()
    document.add_paragraph("1 基本信息", style="Heading 1")
    table = document.add_table(rows=4, cols=4)
    table.cell(0, 0).text = "项目"
    table.cell(0, 1).merge(table.cell(0, 3)).text = "自研成本"
    table.cell(1, 0).text = "指标"
    table.cell(1, 1).text = "研发投入"
    table.cell(1, 2).text = "研发周期"
    table.cell(1, 3).text = "CAS号"
    table.cell(3, 0).text = "技术部意见"
    table.cell(3, 1).merge(table.cell(3, 3))

    outline = build_outline(open_document(_docx(document)))

    cost_cell = outline.by_key()["t0r2c1"]
    assert cost_cell.writable is True
    assert cost_cell.column_hint == "自研成本 › 研发投入"
    assert cost_cell.expect == "number"
    assert outline.by_key()["t0r2c3"].expect == "cas"

    # 意见栏：标签 + 一个跨列空格，语义取行标题，不再去上一块表头里抓「药品名称」
    opinion = outline.by_key()["t0r3c1"]
    assert opinion.writable is True
    assert opinion.row_hint == "技术部意见"
    assert opinion.column_hint == ""
    assert opinion.expect == "opinion"
    assert opinion.col_span == 3
    assert opinion.label.startswith("表1 · 技术部意见")

    # 行标题列里的空格是版面留白，不当可写位置
    assert outline.by_key()["t0r2c0"].writable is False


def test_multi_column_row_without_header_semantics_is_not_writable() -> None:
    """一排空格又看不出每列含义：不可写，避免模型按顺序把值塞进去。"""
    document = Document()
    document.add_paragraph("1 数据", style="Heading 1")
    table = document.add_table(rows=2, cols=3)
    table.cell(0, 0).text = "序号"

    outline = build_outline(open_document(_docx(document)))

    for col in (1, 2):
        cell = outline.by_key()[f"t0r1c{col}"]
        assert cell.writable is False
        assert "看不出每列要填什么" in (cell.reason or "")


def _cover_template(empty_lines: int = 10) -> DocxDocument:
    """封面（连续空段）+ 目录 + 正文，复现线上「首页被写正文」的母本形态。"""
    document = Document()
    for _ in range(empty_lines):
        document.add_paragraph("")
    document.add_paragraph("文件名称：技术调研报告")  # 封面上的标签行
    document.add_paragraph("目录", style="Heading 1")
    document.add_paragraph("1 综合信息", style="Heading 2")
    document.add_paragraph("")  # 正文空位：仍要可写
    return document


def test_cover_region_is_not_writable() -> None:
    outline = build_outline(open_document(_docx(_cover_template())))

    # 封面（首个标题之前的连续空段）整区禁写，原因要能看懂
    for key in ("p0", "p1", "p9"):
        item = outline.by_key()[key]
        assert item.writable is False
        assert "封面" in (item.reason or "")
        assert item.label.startswith("封面第")

    # 目录之后的正文空段不受影响
    body = outline.by_key()["p13"]
    assert body.writable is True
    assert body.label.startswith("正文第")


def test_cover_keeps_label_paragraph_writable() -> None:
    """封面上的「文件编号：」只差一个值，不能因为整区禁写一起锁掉。"""
    document = Document()
    document.add_paragraph("")
    document.add_paragraph("")
    document.add_paragraph("")
    document.add_paragraph("文件编号：")
    document.add_paragraph("目录", style="Heading 1")
    document.add_paragraph("")  # 正文

    outline = build_outline(open_document(_docx(document)))

    label = outline.by_key()["p3"]
    assert label.writable is True
    assert label.append is True
    assert "封面" in label.label


def test_cover_detected_by_cover_words() -> None:
    """没有「连续 3 个空段」，但前置区出现「密级」这类封面字段：同样按封面处理。"""

    def _doc_with_cover_line(with_secret: bool) -> DocxDocument:
        document = Document()
        if with_secret:
            document.add_paragraph("密级：内部")
        document.add_paragraph("")
        document.add_paragraph("")
        document.add_paragraph("1 综合信息", style="Heading 1")
        document.add_paragraph("")
        return document

    with_cover = build_outline(open_document(_docx(_doc_with_cover_line(True))))
    # p1/p2 在封面区内：即使只有 2 个连续空段，也一并锁掉
    assert with_cover.by_key()["p1"].writable is False
    assert "封面" in (with_cover.by_key()["p1"].reason or "")

    # 去掉封面字段名后，同样两个空段不再被判封面（证明锁定来自封面判定）
    without_cover = build_outline(open_document(_docx(_doc_with_cover_line(False))))
    assert without_cover.by_key()["p0"].writable is True


def test_no_cover_keeps_front_paragraphs_writable() -> None:
    """反例：文档没有封面（标题开头，或标题前就是正文），不能误锁。"""
    # 1) 第一个标题之前只有 1 个空段：不满足「连续 ≥3 空段」也不含封面词
    document = Document()
    document.add_paragraph("")
    document.add_paragraph("1 综合信息", style="Heading 1")
    document.add_paragraph("")
    assert build_outline(open_document(_docx(document))).by_key()["p0"].writable is True

    # 2) 标题之前已经有两段长正文：按正文看，不判封面
    prose = Document()
    prose.add_paragraph(
        "这是一段完整的正文内容，用于说明本报告的范围与依据，长度超过四十个字以便判定为正文而不是封面版式。"
    )
    prose.add_paragraph("这是第二段完整的正文内容，同样超过四十个字，用来确认前置区不是封面而是正文开头部分。")
    prose.add_paragraph("1 综合信息", style="Heading 1")
    prose.add_paragraph("")
    outline = build_outline(open_document(_docx(prose)))
    assert outline.by_key()["p0"].writable is False  # 已有完整文字，本来就不可写
    assert outline.by_key()["p3"].writable is True


def test_cover_table_cells_are_locked() -> None:
    """封面里的表格（抬头/文件名称）也是版面，整表禁写并标「封面 ·」。"""
    document = Document()
    document.add_paragraph("")
    document.add_paragraph("")
    document.add_paragraph("")
    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "文件名称"
    document.add_paragraph("目录", style="Heading 1")
    document.add_paragraph("")

    outline = build_outline(open_document(_docx(document)))

    cell = outline.by_key()["t0r0c1"]
    assert cell.writable is False
    assert cell.label.startswith("封面 · ")
    assert "封面" in (cell.reason or "")
