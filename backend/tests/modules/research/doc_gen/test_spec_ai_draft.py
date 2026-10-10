"""AI 语义增强：只改语义、不碰锚点，检索词并集，低置信转 needs_review，失败静默降级。"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from app.modules.research.doc_gen import service, spec_ai_draft, spec_source
from app.modules.research.doc_gen.template_spec import Anchor, Slot, TemplateSpec


class _FakeLLM:
    """替身 LLM：返回预置 payload，或抛出预置异常以验证降级。"""

    def __init__(self, payload: Any) -> None:
        self._payload = payload
        self.calls = 0

    async def chat_json(self, messages: Any, expected_keys: Any = None, temperature: float = 0, **kwargs: Any) -> Any:
        self.calls += 1
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _spec() -> TemplateSpec:
    return TemplateSpec(
        code="t",
        name="测试模板",
        version="1",
        stage="lab",
        master_asset="",
        slots=[
            Slot(
                key="route_1",
                label="工艺路线1",
                kind="paragraph",
                anchors=[Anchor(type="section_body", heading="工艺路线")],
            ),
            Slot(
                key="yield_1",
                label="收率",
                kind="field",
                expects="text",
                search_terms=["收率"],
                anchors=[Anchor(type="paragraph_after_label", paragraph_label="收率：")],
            ),
        ],
    )


async def test_enrich_merges_terms_and_sets_review_state() -> None:
    """高置信→auto、低置信→needs_review；检索词并集；语义字段增强；锚点/kind 不动。"""
    spec = _spec()
    before_anchors = [slot.anchors[0].model_dump() for slot in spec.slots]
    payload = {
        "slots": [
            {
                "key": "route_1",
                "label": "工艺路线",
                "search_terms": ["route", "合成路线"],
                "query_hint": "填工艺步骤",
                "expects": "text",
                "required": True,
                "confidence": 0.9,
            },
            {
                "key": "yield_1",
                "label": "收率",
                "search_terms": ["yield", "产率"],
                "expects": "percent",
                "unit": "%",
                "confidence": 0.3,
            },
        ]
    }
    result = await spec_ai_draft.enrich_spec_semantics(_spec(), llm=_FakeLLM(payload))
    route = next(slot for slot in result.slots if slot.key == "route_1")
    yield_ = next(slot for slot in result.slots if slot.key == "yield_1")

    assert route.review_state == "auto"  # 0.9 ≥ 阈值
    assert yield_.review_state == "needs_review"  # 0.3 < 阈值
    assert "收率" in yield_.search_terms and "yield" in yield_.search_terms  # 并集
    assert route.required is True
    assert yield_.expects == "percent" and yield_.unit == "%"
    # 锚点与 kind 绝不被 AI 改动（渲染安全铁律）
    assert [slot.anchors[0].model_dump() for slot in result.slots] == before_anchors
    assert [slot.kind for slot in result.slots] == ["paragraph", "field"]


async def test_enrich_degrades_on_llm_failure() -> None:
    """LLM 抛错时静默降级：原样返回，review_state 不被误标。"""
    llm = _FakeLLM(RuntimeError("boom"))
    result = await spec_ai_draft.enrich_spec_semantics(_spec(), llm=llm)
    assert all(slot.review_state == "auto" for slot in result.slots)
    assert llm.calls >= 1


async def test_enrich_skips_invalid_and_unknown_keys() -> None:
    """未知 key 跳过；非法 expects 被忽略（保持原值），但同条的合法字段仍应用。"""
    payload = {
        "slots": [
            {"key": "不存在的key", "search_terms": ["x"], "confidence": 0.9},
            {"key": "yield_1", "expects": "非法类型", "search_terms": ["产率"], "confidence": 0.8},
        ]
    }
    result = await spec_ai_draft.enrich_spec_semantics(_spec(), llm=_FakeLLM(payload))
    yield_ = next(slot for slot in result.slots if slot.key == "yield_1")
    assert yield_.expects == "text"  # 非法值未覆盖原值
    assert "产率" in yield_.search_terms  # 合法字段仍生效
    assert yield_.review_state == "auto"  # 0.8 ≥ 阈值


async def test_enrich_skips_non_enrichable_slots() -> None:
    """图片/系统字段/纯人工槽位不送 AI 增强（_enrichable 过滤）。"""
    spec = TemplateSpec(
        code="t2",
        name="测试",
        version="1",
        stage="lab",
        master_asset="",
        slots=[
            Slot(key="logo", label="LOGO", kind="image", anchors=[Anchor(type="image_placeholder")]),
            Slot(
                key="doc_code",
                label="编码",
                kind="field",
                from_meta=True,
                anchors=[Anchor(type="header_field", header_contains="编码")],
            ),
            Slot(
                key="manual",
                label="人工",
                kind="field",
                manual_only=True,
                anchors=[Anchor(type="paragraph_after_label", paragraph_label="人工：")],
            ),
        ],
    )
    llm = _FakeLLM({"slots": []})
    result = await spec_ai_draft.enrich_spec_semantics(spec, llm=llm)
    assert llm.calls == 0  # 无可增强槽位，根本不调用 LLM
    assert all(slot.review_state == "auto" for slot in result.slots)


# ===== service.enrich_template_semantics：如实汇报真实变更槽位数 =====


def _patch_service_enrich(
    monkeypatch: pytest.MonkeyPatch, template: Any, spec: TemplateSpec, fake_enrich: Callable[..., Awaitable[Any]]
) -> None:
    """把 service 增强路径的外部依赖全部换成替身：不连库、不调真模型。"""

    async def _load(_session: Any, _tid: Any) -> Any:
        return template

    async def _resolve(_session: Any, _template: Any) -> TemplateSpec:
        return spec

    async def _config() -> Any:
        return SimpleNamespace(template_model_name="m", llm_call_timeout_seconds=5.0, confidence_mid=0.5)

    async def _model(_name: Any, _kind: Any) -> Any:
        return SimpleNamespace(model_override="mo", config_name="cn")

    monkeypatch.setattr(service, "_load_template_or_404", _load)
    monkeypatch.setattr(spec_source, "resolve_for_template", _resolve)
    monkeypatch.setattr(service, "load_runtime_config", _config)
    monkeypatch.setattr(service, "resolve_model", _model)
    monkeypatch.setattr(service, "enrich_spec_semantics", fake_enrich)


async def test_service_enrich_counts_only_changed_slots(monkeypatch: pytest.MonkeyPatch) -> None:
    """只有实际发生字段变更的槽位计入 enriched_slots，不再把总数谎报成增强数。"""
    template = SimpleNamespace(id=uuid4(), template_structure={})

    async def _enrich(sp: TemplateSpec, **_kw: Any) -> TemplateSpec:
        sp.slots[1].search_terms = [*sp.slots[1].search_terms, "产率"]  # 仅 yield_1 变更
        return sp

    _patch_service_enrich(monkeypatch, template, _spec(), _enrich)
    result = await service.enrich_template_semantics(None, uuid4())  # type: ignore[arg-type]
    assert result["total_slots"] == 2
    assert result["enriched_slots"] == 1
    assert template.template_structure["slots"][1]["search_terms"] == ["收率", "产率"]


async def test_service_enrich_zero_when_degraded(monkeypatch: pytest.MonkeyPatch) -> None:
    """AI 降级未改任何槽位时 enriched_slots=0，前端据此提示人工核对而非谎报成功。"""
    template = SimpleNamespace(id=uuid4(), template_structure={})

    async def _enrich(sp: TemplateSpec, **_kw: Any) -> TemplateSpec:
        return sp  # 静默降级：原样返回

    _patch_service_enrich(monkeypatch, template, _spec(), _enrich)
    result = await service.enrich_template_semantics(None, uuid4())  # type: ignore[arg-type]
    assert result["enriched_slots"] == 0
    assert result["total_slots"] == 2
