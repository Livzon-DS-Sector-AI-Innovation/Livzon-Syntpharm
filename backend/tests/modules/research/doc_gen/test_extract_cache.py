"""提取缓存测试：缓存键对每个维度敏感、结果序列化往返、脏数据降级。"""

from __future__ import annotations

from app.modules.research.doc_gen import extract_cache, status
from app.modules.research.doc_gen.extraction import EvidenceModel, SlotResult


def test_cache_key_sensitive_to_each_dimension() -> None:
    """模板 / 槽位 / 候选内容 / 模型档位 任一变化都必须换键（否则会串用结果）。"""
    cache = extract_cache.DbExtractCache(template_code="tech_research_report", model_note="m1")
    base = cache.key("originator", "hash1")

    assert base == cache.key("originator", "hash1")  # 同输入稳定
    assert base != cache.key("drug_name", "hash1")  # 槽位变化
    assert base != cache.key("originator", "hash2")  # 候选内容变化
    assert base != extract_cache.DbExtractCache(template_code="other", model_note="m1").key("originator", "hash1")
    assert base != extract_cache.DbExtractCache(template_code="tech_research_report", model_note="m2").key(
        "originator", "hash1"
    )


def test_result_payload_roundtrip() -> None:
    """SlotResult 落库形态可无损往返（含证据、归因、置信度）。"""
    result = SlotResult(
        key="originator",
        text="AstraZeneca AB",
        state=status.STATUS_NEEDS_VERIFY,
        reason="引用经模糊匹配核对",
        evidence=[EvidenceModel(file_id="m1", page=2, quote="原研企业：AstraZeneca AB")],
        candidates=["候选值"],
        confidence=0.8,
        gap_reason="fuzzy_evidence",
    )

    restored = extract_cache.result_from_payload(extract_cache.result_to_payload(result))

    assert restored is not None
    assert restored.key == result.key
    assert restored.text == result.text
    assert restored.state == result.state
    assert restored.reason == result.reason
    assert restored.evidence[0].quote == result.evidence[0].quote
    assert restored.candidates == result.candidates
    assert restored.confidence == result.confidence
    assert restored.gap_reason == result.gap_reason


def test_broken_payload_degrades_to_miss() -> None:
    """缓存体被人为改坏时按未命中处理，不抛异常。"""
    assert extract_cache.result_from_payload(None) is None
    assert extract_cache.result_from_payload({"no_key": True}) is None
    assert extract_cache.result_from_payload({"key": "a", "evidence": [123]}) is None
