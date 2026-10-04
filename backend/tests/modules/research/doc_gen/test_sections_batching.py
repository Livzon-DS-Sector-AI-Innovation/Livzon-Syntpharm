"""章节语义分组测试：section 只补空、章节对齐切批不把批切碎。"""

from __future__ import annotations

from typing import Any

from app.modules.research.doc_gen.extraction import SlotExtractor
from app.modules.research.doc_gen.parsing import TextBlock
from app.modules.research.doc_gen.template_analyzer import (
    TemplateAnalysisResult,
    apply_sections_to_spec,
)
from app.modules.research.doc_gen.templates import get_template_spec

BLOCKS = [TextBlock(file_id="m1", page=1, index=0, text="资料", kind="paragraph")]


class _NullLLM:
    """切批测试不触发模型调用，只需一个占位客户端。"""

    async def chat_json(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return {"slots": []}


def _slots(sections: list[str]) -> list[Any]:
    """按给定章节序列造一组同来源的槽位（沿用真实模板槽位定义）。"""
    base = get_template_spec("tech_research_report").slots[0]
    return [
        base.model_copy(update={"key": f"s{index}", "label": f"槽{index}", "section": section})
        for index, section in enumerate(sections)
    ]


def _batches(sections: list[str], batch_size: int) -> list[list[str]]:
    spec = get_template_spec("tech_research_report")
    slots = _slots(sections)
    extractor = SlotExtractor(
        spec.model_copy(update={"slots": slots}),
        BLOCKS,
        batch_size=batch_size,
        llm=_NullLLM(),
    )
    return [[slot.key for slot in batch] for batch in extractor._batches(slots)]


def test_section_change_splits_only_when_batch_is_large_enough() -> None:
    """章节变化时只在「当前批已够大」（≥ 批大小一半）才收口。"""
    # 批大小 6、half=3：[A,A,A] 已够大 → 遇 B 收口；[B,B] 不够大但已到末尾
    assert _batches(["A", "A", "A", "B", "B"], 6) == [["s0", "s1", "s2"], ["s3", "s4"]]


def test_short_sections_stay_together() -> None:
    """各章只有一两个槽位时不许切碎：全部留在一批里。"""
    assert _batches(["A", "B", "C"], 6) == [["s0", "s1", "s2"]]


def test_batch_size_still_caps_a_long_section() -> None:
    """同一章节槽位很多时仍受批大小上限约束。"""
    assert _batches(["A"] * 8, 6) == [["s0", "s1", "s2", "s3", "s4", "s5"], ["s6", "s7"]]


def test_without_section_falls_back_to_plain_chunking() -> None:
    """全部没有章节信息（旧模板/分析未产出）时退回原顺序切批。"""
    assert _batches([""] * 5, 2) == [["s0", "s1"], ["s2", "s3"], ["s4"]]


def test_apply_sections_only_fills_empty() -> None:
    """章节回写只补空值：人工/识别流程已写入的章节不被 AI 覆盖。"""
    spec = get_template_spec("tech_research_report").model_copy(deep=True)
    first, second = spec.slots[0], spec.slots[1]
    first.section = "人工章节"
    analysis = TemplateAnalysisResult(sections={first.key: "AI章节", second.key: "工艺研究"})

    applied = apply_sections_to_spec(spec, analysis)

    assert applied == 1
    assert first.section == "人工章节"
    assert second.section == "工艺研究"
