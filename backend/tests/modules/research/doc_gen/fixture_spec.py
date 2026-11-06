"""测试用的内置模板规格快照。

历史上测试直接从生产代码 `doc_gen/templates/` 取规格。该注册表已删除——填充项统一以
「交付物模板行上落库的 template_structure」为唯一来源，存量内置模板由 0113 迁移回填。

这里读取的 JSON 与 0113 迁移用的是同一份快照，因此测试仍然覆盖那 37 个已标定槽位的
语义（`manual_only` / `from_meta` / `compute` 列等），不依赖任何生产代码。
"""

from __future__ import annotations

from pathlib import Path

from app.modules.research.doc_gen.template_spec import TemplateSpec

# backend/tests/modules/research/doc_gen/fixture_spec.py -> backend/
_BACKEND_ROOT = Path(__file__).resolve().parents[4]
SPEC_PATH = _BACKEND_ROOT / "alembic" / "data" / "doc_gen" / "tech_research_report_spec.json"


def builtin_spec() -> TemplateSpec:
    """返回内置规格快照的深拷贝（测试可随意 model_copy/改字段，不互相污染）。"""
    return TemplateSpec.model_validate_json(SPEC_PATH.read_text(encoding="utf-8"))
