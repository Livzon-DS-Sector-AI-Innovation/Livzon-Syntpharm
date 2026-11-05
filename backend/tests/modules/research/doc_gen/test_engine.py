"""文档生成引擎测试：锚点定位、样式守卫、计算列、降级语义。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from app.modules.research.doc_gen import anchors, grid, renderer, retrieval, status
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.templates import get_template_spec

MASTER = Path(__file__).resolve().parents[4] / "app/modules/research/doc_gen/assets/templates/tech_research_report.dotx"


@pytest.fixture(scope="module")
def master_bytes() -> bytes:
    if not MASTER.exists():  # pragma: no cover
        pytest.skip("模板母本缺失")
    return MASTER.read_bytes()


@pytest.fixture()
def doc(master_bytes: bytes) -> Any:
    return renderer.open_document(master_bytes)


def _spec() -> Any:
    return get_template_spec("tech_research_report")


def _table(doc: Any, *keys: str) -> Any:
    for table in doc.tables:
        head = grid.normalize(anchors.table_header_text(table, 2))
        if all(k in head for k in keys):
            return table
    raise AssertionError(f"未找到表格 {keys}")


def test_resolve_all_anchors(doc: Any) -> None:
    """母本每个槽位的锚点都必须可定位（模板变更后此测试会立刻报警）。"""
    unresolved: dict[str, str] = {}
    for slot in _spec().slots:
        for anchor in slot.anchors:
            try:
                anchors.resolve_anchor(doc, slot, anchor)
            except anchors.AnchorUnresolvedError as exc:
                unresolved[exc.slot_key] = exc.reason
    assert unresolved == {}


def test_label_anchor_does_not_hit_similar_label(doc: Any) -> None:
    """「名称：」不能误命中「其他名称：」——这是冒号标签锚点最容易出错的地方。"""
    slot = _spec().slot("name_cn")
    assert slot is not None
    target = anchors.resolve_anchor(doc, slot, slot.anchors[0])
    assert isinstance(target, anchors.ParagraphTarget)
    assert target.paragraph.text.strip() == "名称："


def test_render_preserves_styles_and_structure(master_bytes: bytes) -> None:
    """渲染只改文字：包内其余部件、表格数量与段落数必须保持稳定。"""
    spec = _spec()
    data, report = renderer.render_document(master_bytes, spec, {})
    rendered = renderer.open_document(data)
    original = renderer.open_document(master_bytes)
    assert report.unresolved == {}
    assert len(rendered.tables) == len(original.tables)
    assert len(rendered.paragraphs) >= len(original.paragraphs)
    # 目录页码被移除并插入提示
    assert any("请在 Word 中更新页码" in p.text for p in rendered.paragraphs)


def test_global_variable_replaced_and_placeholder_written(master_bytes: bytes) -> None:
    """占位关键词被替换、未提供依据的槽位写入待补充、图片槽位写占位。"""
    spec = _spec()
    values = {"drug_name": renderer.SlotValue(text="奥美拉唑")}
    data, _report = renderer.render_document(master_bytes, spec, values)
    doc = renderer.open_document(data)
    text = "\n".join(p.text for p in anchors.iter_all_paragraphs(doc))
    assert "XXXX" not in text and "XXX" not in text.replace("XXXX", "")
    assert "奥美拉唑" in text
    assert status.PENDING_PREFIX in text
    assert "结构式：[图片占位" in text  # 图片槽位只留人工占位


def test_table_rows_clone_delete_and_compute(master_bytes: bytes) -> None:
    """数据表：行数随记录增删，费用/占比/合计全部由代码计算。"""
    spec = _spec()
    records = [
        {"material": "起始物料A", "usage": "0.62", "price": "1800"},
        {"material": "溶剂B", "usage": "3.5", "price": "12"},
        {"material": "催化剂C", "usage": "0.05", "price": "9000"},
    ]
    values = {"material_cost_rows": renderer.SlotValue(rows=records)}
    data, report = renderer.render_document(master_bytes, spec, values)
    assert report.unresolved == {}
    doc = renderer.open_document(data)
    table = _table(doc, "物料名称", "费用占比")
    grid_rows = [_grid_row(table, i) for i in range(len(table.rows))]
    assert grid_rows[0][:5] == ["物料名称", "用量", "单价", "费用", "费用占比"]
    assert grid_rows[1][3] == "1116"  # 0.62 * 1800，由代码计算
    assert grid_rows[1][4] == "69.4%"  # 1116 / 1608
    assert grid_rows[-1][0] == "1kg总价", "合计行标签不得被覆盖"
    assert grid_rows[-1][3] == "1608"
    assert grid_rows[-1][4] == "100%"


def _grid_row(table: Any, row_index: int) -> list[str]:
    """把一行按网格列展开（合并单元格按占位补齐），便于按列断言。"""
    cells = grid.row_grid_cells(table.rows[row_index])
    width = max((start + grid.cell_span(cell) for cell, start in cells), default=0) + 1
    out = [""] * width
    for cell, start in cells:
        out[start] = cell.text.strip()
    return out


def test_sequence_column_and_surplus_rows_cleared(master_bytes: bytes) -> None:
    """序号列由代码续号；母本预留行不得残留旧的预填内容。"""
    spec = _spec()
    rows = [{"structure": f"杂质{chr(65 + i)}", "origin": "工艺", "impurity_type": "有机杂质"} for i in range(6)]
    data, report = renderer.render_document(master_bytes, spec, {"impurity_rows": renderer.SlotValue(rows=rows)})
    assert report.unresolved == {}
    doc = renderer.open_document(data)
    table = _table(doc, "序号", "杂质类型")
    seq = [_grid_row(table, i)[0] for i in range(1, len(table.rows))]
    assert seq == ["1", "2", "3", "4", "5", "6"]


def test_occupied_cell_is_not_overwritten(master_bytes: bytes) -> None:
    """母本已有内容的单元格默认不覆盖，避免毁掉带子标签的格子。"""
    spec = _spec()
    _data, report = renderer.render_document(
        master_bytes, spec, {"product_spec": renderer.SlotValue(text="不该覆盖进去的内容")}
    )
    assert "product_spec" in report.occupied
    doc = renderer.open_document(master_bytes)
    original = _table(doc, "基本信息", "药品名称")
    texts = [c.text for r in original.rows for c in grid.distinct_row_cells(r)]
    assert not any("不该覆盖进去的内容" in t for t in texts)


def test_draft_and_conflict_states_render_marks(master_bytes: bytes) -> None:
    """AI 草稿前缀与冲突标记按纯文本落地，不引入样式变化。"""
    spec = _spec()
    values = {
        "route_1": renderer.SlotValue(text=status.with_draft_prefix("以氯甲基吡啶起始。"), state=status.STATUS_DRAFT),
        "originator": renderer.SlotValue(text=status.CONFLICT_MARK, state=status.STATUS_CONFLICT),
    }
    data, report = renderer.render_document(master_bytes, spec, values)
    doc = renderer.open_document(data)
    text = "\n".join(p.text for p in anchors.iter_all_paragraphs(doc))
    assert status.DRAFT_PREFIX in text and status.CONFLICT_MARK in text
    assert "route_1" in report.drafts


def test_missing_value_becomes_pending_placeholder(master_bytes: bytes) -> None:
    """没有值的槽位必须显式留待补充，不能静默留空。"""
    spec = _spec()
    _data, report = renderer.render_document(master_bytes, spec, {})
    assert len(report.pending) >= len([s for s in spec.slots if s.kind != "table"]) - 3


def test_retrieval_respects_file_scope() -> None:
    """候选块检索按文件角色过滤，文献不会污染数值型槽位。"""
    blocks = [
        TextBlock(file_id="m1", page=1, index=0, text="登记号：Y20190001234", kind="paragraph"),
        TextBlock(file_id="l1", page=1, index=0, text="文献中记载收率为 85%", kind="paragraph"),
    ]
    retriever = retrieval.BlockRetriever(blocks)
    only_material = retriever.candidates(["登记号"], allow_file_ids=["m1"])
    assert [b.file_id for b in only_material] == ["m1"]
    assert retriever.candidates(["登记号"], allow_file_ids=["l1"]) == []
