"""槽位定义的解析来源。

唯一来源是**交付物模板行上的 `template_structure`**：上传母本时由 `spec_draft` 按母本
结构自动识别并落库，此后人工补充的填写项、人工确认的语义都写在同一列上。

这里刻意没有「代码内置规格」这条回退：曾经存在双轨（代码注册表 + 落库结构），导致同一份
母本可能走不同轨道、改内置必须发版、界面还要解释哪套配置生效。存量内置模板的结构已在
0113 迁移里一次性回填，因此现在解析不到结构就是真的没有可用配置。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.doc_gen.template_spec import TemplateSpec

logger = logging.getLogger(__name__)


def spec_from_structure(structure: Any, *, code_hint: str = "") -> TemplateSpec | None:
    """把落库的 `template_structure` 还原为规格；非法结构返回 None（记 ERROR 便于排查）。"""
    if not isinstance(structure, dict) or not structure.get("slots"):
        return None
    try:
        return TemplateSpec.model_validate(structure)
    except Exception:  # noqa: BLE001 - 结构可能被人工改坏，降级而不是让任务崩
        logger.exception("template_structure 无法解析为槽位定义", extra={"code": code_hint})
        return None


def resolve_spec(code: str, structure: Any = None) -> TemplateSpec:
    """把落库结构解析为规格；结构缺失或非法则抛 KeyError。

    `code` 只用于日志与错误信息，不再用于回查代码注册表。
    """
    spec = spec_from_structure(structure, code_hint=code)
    if spec is not None:
        return spec
    raise KeyError(f"该模板没有可用的填充项结构，请重新上传 Word 母本: {code}")


async def _structure_of(session: AsyncSession, code: str, template_id: str | None) -> Any:
    """按模板 id（优先）或 code 取落库的结构。

    按 id 命中时**不过滤软删**：模板被删后，历史任务重跑/回看仍需要它当时的填充项结构，
    否则只能报「模板缺失」。按 code 兜底查询时才要求未删除。
    """
    from app.modules.research.models import RdDeliverableTemplate

    if template_id:
        try:
            row = await session.get(RdDeliverableTemplate, uuid.UUID(template_id))
        except (ValueError, TypeError):
            row = None
        if row is not None:
            return row.template_structure
    if not code:
        return None
    row = (
        (
            await session.execute(
                select(RdDeliverableTemplate)
                .where(
                    RdDeliverableTemplate.template_code == code,
                    RdDeliverableTemplate.is_deleted.is_(False),
                )
                .order_by(RdDeliverableTemplate.created_at.desc())
                .limit(1)
            )
        )
        .scalars()
        .first()
    )
    return None if row is None else row.template_structure


async def resolve_by_code(session: AsyncSession, code: str) -> TemplateSpec:
    """只给 code 时取规格：回库找同 code 的落库结构。"""
    return resolve_spec(code, await _structure_of(session, code, None))


async def resolve_for_template(session: AsyncSession, template: Any) -> TemplateSpec:
    """按交付物模板行取规格（上传/建任务时用）。"""
    return resolve_spec(template.template_code or "", template.template_structure)


async def resolve_for_job(session: AsyncSession, job: Any) -> TemplateSpec:
    """按任务取规格：任务只留了 code，结构需要回模板行取。

    优先用任务创建时写入的 `deliverable_template_id`，避免「同 code 多母本」时取错。
    """
    template_id = str((job.meta or {}).get("deliverable_template_id") or "") or None
    structure = await _structure_of(session, job.template_code, template_id)
    return resolve_spec(job.template_code, structure)


__all__ = [
    "resolve_by_code",
    "resolve_for_job",
    "resolve_for_template",
    "resolve_spec",
    "spec_from_structure",
]
