"""母本结构自动识别：生成的槽位定义必须自洽——每个槽位都能在同一份母本里定位。"""

from __future__ import annotations

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


def test_spec_from_code_priority() -> None:
    """代码内置规格优先于落库结构。"""
    from app.modules.research.doc_gen.templates import get_template_spec

    spec = get_template_spec("tech_research_report")
    bogus = spec.model_copy(update={"name": "被篡改的名字"}).model_dump(mode="json")
    resolved = spec_source.resolve_spec("tech_research_report", bogus)
    assert resolved.name == spec.name


def test_drafted_spec_renders_document() -> None:
    """自动识别的规格必须真的能渲染：全部取不到值时也要产出 docx（只留占位）。"""
    from app.modules.research.doc_gen.renderer import SlotValue, render_document

    data, spec = _draft()
    values = {
        slot.key: SlotValue(text="[待补充：自动识别自检]", rows=[], state="pending") for slot in spec.slots
    }
    docx_bytes, report = render_document(data, spec, values)
    assert docx_bytes[:2] == b"PK"  # zip 容器头，确认是可用的 docx
    assert report.written > 0
    assert not report.unresolved
