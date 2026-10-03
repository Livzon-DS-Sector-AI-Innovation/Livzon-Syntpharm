"""母本结构自动识别：生成的槽位定义必须自洽——每个槽位都能在同一份母本里定位。"""

from __future__ import annotations

import io

from docx import Document

from app.modules.research.doc_gen import spec_source
from app.modules.research.doc_gen.anchors import AnchorUnresolvedError, resolve_slot
from app.modules.research.doc_gen.renderer import open_document
from app.modules.research.doc_gen.service import MIN_ANCHOR_HIT_RATIO, probe_template_match
from app.modules.research.doc_gen.spec_draft import draft_spec_from_bytes, summarize_spec
from app.modules.research.doc_gen.template_spec import TEMPLATE_DIR, TemplateSpec

ASSET = TEMPLATE_DIR / "tech_research_report.dotx"


def _draft() -> tuple[bytes, TemplateSpec]:
    data = ASSET.read_bytes()
    return data, draft_spec_from_bytes(data, name="技术调研报告")


def _table_doc(header_rows: list[list[str]], data_rows: list[list[str]]) -> bytes:
    """构造只含一张表格的 docx：先表头行再数据行，列数取各行最大宽度。"""

    def pad(row: list[str], width: int) -> list[str]:
        return row + [""] * (width - len(row))

    grid = header_rows + data_rows
    width = max(len(row) for row in grid)
    buffer = io.BytesIO()
    doc = Document()
    table = doc.add_table(rows=len(grid), cols=width)
    for r, row in enumerate(grid):
        for c, text in enumerate(pad(row, width)):
            table.rows[r].cells[c].text = text
    doc.save(buffer)
    return buffer.getvalue()


def _tables(spec: TemplateSpec) -> list:
    return [slot for slot in spec.slots if slot.kind == "table"]


def test_draft_covers_main_structures() -> None:
    """表、标签段落、彩色提示语、页眉字段都要被识别出来。"""
    _data, spec = _draft()
    kinds = {slot.kind for slot in spec.slots}
    assert "table" in kinds
    assert "field" in kinds
    assert "paragraph" in kinds
    keys = {slot.key for slot in spec.slots}
    assert "doc_code" in keys
    assert "doc_version" in keys
    assert len(spec.slots) >= 12
    summary = summarize_spec(spec)
    assert summary["slot_count"] == len(spec.slots)


def test_every_drafted_slot_resolves_in_its_own_master() -> None:
    """自洽性：扫描出的槽位若在母本里定位不到，等于生成了一份坏配置。"""
    data, spec = _draft()
    doc = open_document(data)
    unresolved: list[str] = []
    for slot in spec.slots:
        try:
            resolve_slot(doc, slot)
        except AnchorUnresolvedError as exc:
            unresolved.append(f"{slot.key}: {exc.reason}")
    assert unresolved == []


def test_draft_uses_conservative_defaults() -> None:
    """自动识别不猜语义：不引用文献、不做表格计算、字段不允许草稿。"""
    _data, spec = _draft()
    for slot in spec.slots:
        assert slot.required is False
        assert slot.source_roles == ["material"]
        if slot.kind == "table":
            assert all(column.compute == "none" for column in slot.columns)
        if slot.kind in ("field", "image"):
            assert slot.draft_allowed is False


def test_reexport_matches_its_own_draft() -> None:
    """同一份母本再次上传时应命中已生成的配置，而不是又新建一套。"""
    data, spec = _draft()
    probe = probe_template_match(data, [spec])
    assert probe["matched"] == spec.code
    best = probe["best"]
    assert best is not None
    assert best["hit"] / best["total"] >= MIN_ANCHOR_HIT_RATIO


def test_unrelated_doc_is_not_matched() -> None:
    """结构完全不同的 Word 不应被硬套到既有配置上（此时应由调用方转自动识别）。"""
    import io

    from docx import Document

    buffer = io.BytesIO()
    doc = Document()
    doc.add_paragraph("这是一份与任何模板都无关的文档")
    doc.save(buffer)

    probe = probe_template_match(buffer.getvalue())
    assert probe["matched"] is None
    assert MIN_ANCHOR_HIT_RATIO == 0.5


def test_structure_round_trip() -> None:
    """落库的 template_structure 必须能还原成等价规格（生成侧依赖这条）。"""
    _data, spec = _draft()
    restored = spec_source.spec_from_structure(spec.model_dump(mode="json"))
    assert restored is not None
    assert [slot.key for slot in restored.slots] == [slot.key for slot in spec.slots]
    assert restored.code == spec.code
    # 非法/空结构一律返回 None，由调用方降级
    assert spec_source.spec_from_structure({"slots": []}) is None
    assert spec_source.spec_from_structure(None) is None


def test_structure_priority_over_code() -> None:
    """合法落库结构优先于代码内置规格（脱钩编辑生效）；非法/空结构回退代码内置。"""
    from app.modules.research.doc_gen.templates import get_template_spec

    spec = get_template_spec("tech_research_report")
    # 合法但被改名的 structure：structure 优先，应取到改后的名字（脱钩编辑生效）
    edited = spec.model_copy(update={"name": "人工编辑后的名字"}).model_dump(mode="json")
    assert spec_source.resolve_spec("tech_research_report", edited).name == "人工编辑后的名字"
    # 非法 structure（无 slots）：spec_from_structure 返回 None，回退代码内置
    assert spec_source.resolve_spec("tech_research_report", {"slots": []}).name == spec.name
    # 空 structure：回退代码内置
    assert spec_source.resolve_spec("tech_research_report", None).name == spec.name


def test_drafted_spec_renders_document() -> None:
    """自动识别的规格必须真的能渲染：全部取不到值时也要产出 docx（只留占位）。"""
    from app.modules.research.doc_gen.renderer import SlotValue, render_document

    data, spec = _draft()
    values = {slot.key: SlotValue(text="[待补充：自动识别自检]", rows=[], state="pending") for slot in spec.slots}
    docx_bytes, report = render_document(data, spec, values)
    assert docx_bytes[:2] == b"PK"  # zip 容器头，确认是可用的 docx
    assert report.written > 0
    assert not report.unresolved


# ---------------------------------------------------------------------------
# 表格识别放宽（填充项不完整最集中的来源：占位符/序号同义词/表头空格/双行表头）
# ---------------------------------------------------------------------------


def test_placeholder_only_table_recognized_with_review() -> None:
    """数据行全为「/」占位符：旧「严格全空」规则整表漏掉，新规则识别并标需人工核对。"""
    data = _table_doc([["批号", "纯度", "收率"]], [["/", "/", "/"]])
    spec = draft_spec_from_bytes(data, name="占位表")
    tables = _tables(spec)
    assert len(tables) == 1
    assert tables[0].review_state == "needs_review"
    resolve_slot(open_document(data), tables[0])


def test_strictly_empty_table_stays_auto_confidence() -> None:
    """真全空数据行（无任何放宽）仍按 auto 置信度识别，行为向后兼容。"""
    data = _table_doc([["批号", "纯度", "收率"]], [["", "", ""]])
    spec = draft_spec_from_bytes(data, name="空表")
    tables = _tables(spec)
    assert len(tables) == 1
    assert tables[0].review_state == "auto"


def test_seq_synonym_column_exempted_from_blank_check() -> None:
    """序号列叫「编号」且预填 1/2：旧规则因首列非空判「无空行」整表漏掉，同义词扩展后豁免。"""
    data = _table_doc([["编号", "项目", "结果"]], [["1", "", ""], ["2", "", ""]])
    spec = draft_spec_from_bytes(data, name="编号表")
    tables = _tables(spec)
    assert len(tables) == 1
    assert tables[0].table is not None and tables[0].table.sequence_column == "c1"
    resolve_slot(open_document(data), tables[0])


def test_single_blank_header_cell_filled_and_reviewed() -> None:
    """表头恰有一格为空（合并表头常见）：补「列N」列名成槽，补出来的列名不进锚点关键词。"""
    data = _table_doc([["项目", "", "结果"]], [["", "", ""]])
    spec = draft_spec_from_bytes(data, name="缺格表头")
    tables = _tables(spec)
    assert len(tables) == 1
    table = tables[0]
    assert [c.label for c in table.columns] == ["项目", "列2", "结果"]
    assert table.review_state == "needs_review"
    assert table.anchors[0].table_header == ["项目", "结果"]
    resolve_slot(open_document(data), table)


def test_double_header_uses_second_row() -> None:
    """首行全空、次行为真表头（双行表头）：用第二行做列语义，header_rows=2。"""
    data = _table_doc([["", ""], ["纯度", "收率"]], [["", ""]])
    spec = draft_spec_from_bytes(data, name="双行表头")
    tables = _tables(spec)
    assert len(tables) == 1
    table = tables[0]
    assert table.table is not None and table.table.header_rows == 2
    assert table.review_state == "needs_review"
    resolve_slot(open_document(data), table)


def test_filled_table_not_recognized() -> None:
    """数据全部填好的固定表（无空行无占位符）仍不识别——放宽只救「待填」，不猜成品表。"""
    data = _table_doc([["批号", "纯度"]], [["A001", "99.5%"]])
    spec = draft_spec_from_bytes(data, name="成品表")
    assert _tables(spec) == []
    assert [slot for slot in spec.slots if slot.key.startswith("cell_")] == []


def test_repeat_mark_placeholder_recognized() -> None:
    """数据行用「XXX」标记待填：旧占位符集合不含 X，整表判「无待填迹象」而漏掉。"""
    data = _table_doc(
        [["项目名称", "研究内容", "工艺路线", "批号", "数量", "结果"]],
        [["XXX", "关键原料", "SM-01", "XXX", "XXX", "XXX"]],
    )
    spec = draft_spec_from_bytes(data, name="XXX表")
    tables = _tables(spec)
    assert len(tables) == 1
    assert tables[0].review_state == "needs_review"
    resolve_slot(open_document(data), tables[0])


def test_row_label_table_recognized() -> None:
    """首列是固定行标签、其余格全空的表（行标签型）：旧规则要求整行全空，永远不成立。"""
    data = _table_doc(
        [["项目", "评估结果", "奖金基数", "激励节点"]],
        [["技术难度", "", "", ""], ["完成质量", "", "", ""]],
    )
    spec = draft_spec_from_bytes(data, name="行标签表")
    tables = _tables(spec)
    assert len(tables) == 1
    assert tables[0].review_state == "needs_review"
    resolve_slot(open_document(data), tables[0])


def test_key_value_table_yields_cell_slots() -> None:
    """起草人/审核人签署表：首行空格过半，按整表生成会编造行，改按格定位。"""
    data = _table_doc(
        [["起草人", "", "", "年月日"]],
        [["", "姓名（职务）", "", ""], ["", "", "", ""], ["审核人", "姓名（职务）", "", ""]],
    )
    spec = draft_spec_from_bytes(data, name="签署表")
    assert _tables(spec) == []  # 不整表成槽
    cells = [slot for slot in spec.slots if slot.key.startswith("cell_")]
    assert {slot.label for slot in cells} >= {"起草人", "审核人"}
    assert all(slot.review_state == "needs_review" for slot in cells)
    doc = open_document(data)
    for slot in cells:
        assert resolve_slot(doc, slot)  # 坐标锚点必须真能定位到格子
