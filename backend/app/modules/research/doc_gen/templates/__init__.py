"""内置模板注册表（第一版模板随代码入库，新增模板需发版）。"""

from __future__ import annotations

from app.modules.research.doc_gen.template_spec import TemplateSpec
from app.modules.research.doc_gen.templates.tech_research_report import SPEC as TECH_RESEARCH_REPORT

_REGISTRY: dict[str, TemplateSpec] = {TECH_RESEARCH_REPORT.code: TECH_RESEARCH_REPORT}


def list_templates() -> list[TemplateSpec]:
    """全部可用模板。"""
    return list(_REGISTRY.values())


def get_template_spec(code: str) -> TemplateSpec:
    """按 code 取模板配置，未注册则抛 KeyError。"""
    if code not in _REGISTRY:
        raise KeyError(f"未注册的文档模板: {code}")
    return _REGISTRY[code]


__all__ = ["get_template_spec", "list_templates"]
