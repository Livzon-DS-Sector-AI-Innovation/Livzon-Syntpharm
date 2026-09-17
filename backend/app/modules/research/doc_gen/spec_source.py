"""槽位定义的解析来源。

优先级：**代码注册表 → 交付物模板行上的 `template_structure`**。

代码注册表里的定义是被 mypy/单测保护的手工标定结果；`template_structure` 是上传母本时
由 `spec_draft` 自动识别出来并落库的配置。两者用同一套 `TemplateSpec` 模型，
因此运行时的 Pydantic 校验、证据回检、算术规则完全一致。
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.research.doc_gen.template_spec import TemplateSpec
from app.modules.research.doc_gen.templates import get_template_spec

logger = logging.getLogger(__name__)


def spec_from_code(code: str) -> TemplateSpec | None:
    """取代码内置规格；未注册返回 None。"""
    if not code:
        return None
    try:
        return get_template_spec(code)
    except KeyError:
        return None


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
    """按优先级取规格；两处都没有则抛 KeyError（调用方转成业务错误）。"""
    spec = spec_from_code(code)
    if spec is not None:
        return spec
    spec = spec_from_structure(structure, code_hint=code)
    if spec is not None:
        return spec
    raise KeyError(f"未注册且没有自动识别配置的文档模板: {code}")


async def _structure_of(session: AsyncSession, code: str, template_id: str | None) -> Any:
    """按模板 id（优先）或 code 取落库的结构。"""
    from app.modules.research.models import RdDeliverableTemplate

    row = None
    if template_id:
        try:
            row = await session.get(RdDeliverableTemplate, uuid.UUID(template_id))
        except (ValueError, TypeError):
            row = None
    if row is None and code:
        row = (
            await session.execute(
                select(RdDeliverableTemplate)
                .where(
                    RdDeliverableTemplate.template_code == code,
                    RdDeliverableTemplate.is_deleted.is_(False),
                )
                .order_by(RdDeliverableTemplate.created_at.desc())
                .limit(1)
            )
        ).scalars().first()
    if row is None or row.is_deleted:
        return None
    return row.template_structure


async def resolve_by_code(session: AsyncSession, code: str) -> TemplateSpec:
    """只给 code 时取规格：代码内置优先，其次回库找同 code 的自动识别结构。"""
    spec = spec_from_code(code)
    if spec is not None:
        return spec
    return resolve_spec(code, await _structure_of(session, code, None))


async def resolve_for_template(session: AsyncSession, template: Any) -> TemplateSpec:
    """按交付物模板行取规格（上传/建任务时用）。"""
    return resolve_spec(template.template_code or "", template.template_structure)


async def resolve_for_job(session: AsyncSession, job: Any) -> TemplateSpec:
    """按任务取规格：任务只留了 code，结构需要回模板行取。

    优先用任务创建时写入的 `deliverable_template_id`，避免「同 code 多母本」时取错。
    """
    spec = spec_from_code(job.template_code)
    if spec is not None:
        return spec
    template_id = str((job.meta or {}).get("deliverable_template_id") or "") or None
    structure = await _structure_of(session, job.template_code, template_id)
    return resolve_spec(job.template_code, structure)


__all__ = [
    "resolve_by_code",
    "resolve_for_job",
    "resolve_for_template",
    "resolve_spec",
    "spec_from_code",
    "spec_from_structure",
]
