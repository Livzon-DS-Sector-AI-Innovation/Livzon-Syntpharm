"""填写项识别结果 Markdown 内容页：母本识别/AI 增强/人工新增的成果肉眼可见。"""

from __future__ import annotations

from app.modules.research.doc_gen.spec_markdown import extract_slot_blocks, render_spec_markdown
from app.modules.research.doc_gen.template_spec import (
    Anchor,
    ColumnSpec,
    SectionFragment,
    Slot,
    TableSpec,
    TemplateSpec,
    Trigger,
)


def _spec(slots: list[Slot] | None = None, fragments: list[SectionFragment] | None = None) -> TemplateSpec:
    return TemplateSpec(
        code="test_md",
        name="Markdown 渲染测试模板",
        version="v1",
        master_asset="tech_research_report.dotx",
        slots=slots or [],
        fragments=fragments or [],
    )


def _field_slot(key: str = "project_name", label: str = "项目名称", **kw: object) -> Slot:
    base: dict[str, object] = {
        "anchors": [Anchor(type="paragraph_after_label", paragraph_label=label)],
    }
    base.update(kw)
    return Slot(key=key, label=label, **base)


def test_render_includes_name_and_slot_marker() -> None:
    """渲染结果应含模板名与每个槽位的 slot 标记，标记内是待填内容区。"""
    spec = _spec([_field_slot("project_name", "项目名称")])
    markdown = render_spec_markdown(spec)
    assert "Markdown 渲染测试模板" in markdown
    assert "<!--slot:project_name-->" in markdown
    assert "<!--/slot-->" in markdown
    assert "**项目名称**" in markdown
    assert "{{待填}}" in markdown


def test_render_shows_only_fill_content() -> None:
    """视图就是模板内容：只展示填写项与待填区，不展示检索词/类型/定位等识别元信息。"""
    slot = _field_slot(
        "yield",
        "收率",
        search_terms=["收率", "yield", "转化率"],
        review_state="needs_review",
        expects="percent",
        required=True,
    )
    markdown = render_spec_markdown(_spec([slot]))
    assert "**收率**" in markdown
    assert "{{待填}}" in markdown
    assert "检索词" not in markdown
    assert "转化率" not in markdown
    assert "需人工核对" not in markdown
    assert "必填" not in markdown
    assert "定位" not in markdown


def test_table_slot_renders_columns() -> None:
    """表格槽位应渲染列头 markdown 表格。"""
    slot = Slot(
        key="route_table",
        label="工艺路线表",
        kind="table",
        columns=[ColumnSpec(key="step", label="步骤"), ColumnSpec(key="yield", label="收率")],
        table=TableSpec(total_row_label="合计"),
        anchors=[
            Anchor(
                type="table_rows",
                table_header=["步骤", "收率"],
                row_label="步骤",
            )
        ],
    )
    markdown = render_spec_markdown(_spec([slot]))
    assert "| 步骤 | 收率 |" in markdown
    assert "| --- | --- |" in markdown
    assert "合计行" not in markdown


def test_extract_slot_blocks_roundtrip() -> None:
    """渲染出的每个槽位标记都能被解析回来，key 与 spec 完全一致。"""
    slots = [_field_slot("a", "甲"), _field_slot("b", "乙")]
    markdown = render_spec_markdown(_spec(slots))
    blocks = extract_slot_blocks(markdown)
    assert set(blocks) == {"a", "b"}
    assert all("{{待填}}" in text for text in blocks.values())


def test_fragment_slots_rendered_and_extractable() -> None:
    """动态章节片段的局部槽位也应渲染并可被标记解析。"""
    fragment = SectionFragment(
        key="route_study",
        label="路线研究",
        title_pool=["路线研究", "合成路线"],
        trigger=Trigger(op="slot_filled", key="a"),
        slots=[_field_slot("condition", "反应条件")],
    )
    markdown = render_spec_markdown(_spec([_field_slot("a", "甲")], fragments=[fragment]))
    assert "## 路线研究" in markdown
    assert "<!--slot:condition-->" in markdown
    assert set(extract_slot_blocks(markdown)) == {"a", "condition"}
