"""研发报告人工填写内容 → 生成上下文：字段整理、虚拟资料落库与对槽位的可见性。"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from app.modules.research.doc_gen import service
from app.modules.research.doc_gen.extraction import SlotExtractor
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.templates import get_template_spec


def _report(**kwargs: Any) -> Any:
    """构造一份报告字段替身（只需要 doc_gen 会读取的字段）。"""
    base: dict[str, Any] = {
        "title": "米诺地尔原料药工艺研究",
        "summary": "本报告总结三批中试结果。",
        "content": "<p>第一批收率 <b>87.5%</b></p><p>第二批收率 88.1%</p>",
        "key_findings": {"summary": "收率稳定", "key_data": "最优温度 60℃", "issues": "杂质略高"},
        "recommendations": "建议放大至 500L。",
        "notes": "",
    }
    base.update(kwargs)
    return SimpleNamespace(**base)


def test_report_context_serializes_all_fields() -> None:
    """人工填写的各字段都要能进上下文，且富文本标签不能残留。"""
    text = service._report_context_text(_report())
    assert "【报告摘要】" in text
    assert "【报告正文】" in text
    assert "第一批收率 87.5%" in text
    assert "<b>" not in text
    assert "【关键数据】" in text
    assert "最优温度 60℃" in text
    assert "【结论与建议】" in text


def test_report_context_skips_empty_report() -> None:
    """全空的报告不应产生一份空资料。"""
    empty = _report(summary=None, content=None, key_findings=None, recommendations=None, title="", notes=None)
    assert service._report_context_text(empty).strip() == ""


async def test_store_report_context_creates_virtual_file(monkeypatch: Any) -> None:
    """有内容时落一条 report_draft 虚拟资料。"""
    saved: dict[str, Any] = {}
    captured: list[Any] = []

    def fake_save(name: str, data: bytes, content_type: str = "") -> str:
        saved["name"] = name
        saved["data"] = data
        return f"local:doc-gen/x/{name}"

    async def fake_add(session: Any, records: list[Any]) -> None:
        captured.extend(records)

    monkeypatch.setattr(service.store, "save_bytes", fake_save)
    monkeypatch.setattr(service.repo, "add_input_files", fake_add)

    await service._store_report_context(None, SimpleNamespace(id=uuid.uuid4()), _report())

    assert len(captured) == 1
    record = captured[0]
    assert record.role == "report_draft"
    assert record.original_filename == service.REPORT_CONTEXT_FILENAME
    assert "【报告摘要】" in saved["data"].decode("utf-8")


async def test_store_report_context_skips_without_report(monkeypatch: Any) -> None:
    """没有关联报告时不应落库。"""
    called = False

    async def fake_add(session: Any, records: list[Any]) -> None:
        nonlocal called
        called = True

    monkeypatch.setattr(service.repo, "add_input_files", fake_add)
    await service._store_report_context(None, SimpleNamespace(id=uuid.uuid4()), None)
    assert not called


def test_report_draft_visible_to_material_slot() -> None:
    """人工填写内容对所有槽位可见，不因 source_roles=material 被过滤。"""
    blocks = [
        TextBlock(file_id="m1", page=1, index=0, text="商品名：洛赛克", kind="paragraph"),
        TextBlock(file_id="report-abc", page=1, index=0, text="【结论与建议】建议放大至 500L", kind="paragraph"),
    ]
    spec = get_template_spec("tech_research_report")
    slot = spec.slot("originator")
    assert slot is not None
    extractor = SlotExtractor(
        spec,
        blocks,
        roles_by_file={"m1": ["material"], "report-abc": ["report_draft"]},
        llm=object(),
    )
    allowed = extractor._allowed_files(slot)
    assert allowed is not None
    assert "report-abc" in allowed
    assert "m1" in allowed
