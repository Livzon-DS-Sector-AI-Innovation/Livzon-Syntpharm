"""模板分析缓存测试：指纹决定复用与失效，脏缓存一律降级为「未命中」。"""

from __future__ import annotations

from app.modules.research.doc_gen import template_cache
from app.modules.research.doc_gen.template_analyzer import SlotGuide, TemplateAnalysisResult
from app.modules.research.doc_gen.template_spec import TemplateSpec
from app.modules.research.doc_gen.templates import get_template_spec

SPEC_CODE = "tech_research_report"


def _spec() -> TemplateSpec:
    return get_template_spec(SPEC_CODE).model_copy(deep=True)


def _analysis() -> TemplateAnalysisResult:
    return TemplateAnalysisResult(
        guides={"originator": SlotGuide(key="originator", key_indicators=["来源", "厂商"], content_pattern="企业名称")},
        enriched_terms={"originator": ["生产厂家", "来源单位"]},
        requirements={"originator": {"unit": "", "cardinality": "single"}},
        sections={"originator": "概述"},
        analyzed_count=1,
    )


def test_fingerprint_is_stable_and_sensitive_to_semantics() -> None:
    """同一份 spec 指纹稳定；语义字段变化必然换指纹；渲染定位字段不参与。"""
    spec = _spec()
    assert template_cache.spec_fingerprint(spec) == template_cache.spec_fingerprint(_spec())

    semantics_changed = _spec()
    semantics_changed.slots[0].search_terms = [*semantics_changed.slots[0].search_terms, "新增同义词"]
    assert template_cache.spec_fingerprint(semantics_changed) != template_cache.spec_fingerprint(spec)

    label_changed = _spec()
    label_changed.slots[0].label = label_changed.slots[0].label + "（改）"
    assert template_cache.spec_fingerprint(label_changed) != template_cache.spec_fingerprint(spec)

    render_only_changed = _spec()
    render_only_changed.slots[0].anchors = []
    assert template_cache.spec_fingerprint(render_only_changed) == template_cache.spec_fingerprint(spec)


def test_cache_roundtrip_through_structure() -> None:
    """写入私有键后可按同一指纹读出等价结果；原有键不受影响。"""
    spec = _spec()
    fingerprint = template_cache.spec_fingerprint(spec)
    structure = {"slots": [{"key": "originator"}], "code": SPEC_CODE}
    payload = template_cache.result_to_payload(_analysis(), fingerprint)
    merged = template_cache.with_cache(structure, payload)

    assert merged["code"] == SPEC_CODE  # 原有键原样保留
    restored = template_cache.cached_result(merged, fingerprint)
    assert restored is not None
    assert restored.guides["originator"].key_indicators == ["来源", "厂商"]
    assert restored.enriched_terms == {"originator": ["生产厂家", "来源单位"]}
    assert restored.sections == {"originator": "概述"}  # 章节标注必须随缓存往返，否则命中即丢
    assert restored.analyzed_count == 1


def test_fingerprint_mismatch_means_miss() -> None:
    """指纹不同（模板被编辑过）必须视为未命中，而不是用过期指引。"""
    fingerprint = template_cache.spec_fingerprint(_spec())
    merged = template_cache.with_cache({}, template_cache.result_to_payload(_analysis(), fingerprint))
    assert template_cache.cached_result(merged, "ffffffffffffffff") is None


def test_broken_cache_degrades_to_miss() -> None:
    """缓存体被人为改坏时按未命中处理，不抛异常。"""
    assert template_cache.cached_result({"slots": []}, "aaaa") is None  # 没有缓存键
    broken = {template_cache.ANALYSIS_CACHE_KEY: {"fingerprint": "aaaa", "guides": {"x": 123}}}
    assert template_cache.cached_result(broken, "aaaa") is None
    assert template_cache.payload_to_result("not-a-dict") is None
