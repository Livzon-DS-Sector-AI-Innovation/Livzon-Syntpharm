"""质量检验台账的数据访问层。"""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import ColumnElement, Select, and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.quality.qc_report.constants import (
    LEVEL_INTERNAL,
    LEVEL_NORMAL,
    LEVEL_OOS,
    LEVEL_SKIP,
    LEVEL_TREND,
)
from app.modules.quality.qc_report.models import QcBatch, QcItem, QcProduct, QcValue


def _alive(model: type[QcProduct] | type[QcItem] | type[QcBatch] | type[QcValue]) -> ColumnElement[bool]:
    return model.is_deleted.is_(False)


async def get_product(db: AsyncSession, product_id: uuid.UUID) -> QcProduct | None:
    stmt = select(QcProduct).where(QcProduct.id == product_id, _alive(QcProduct))
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_product_by_abbr(db: AsyncSession, abbr: str) -> QcProduct | None:
    stmt = select(QcProduct).where(QcProduct.abbr == abbr.upper(), _alive(QcProduct))
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_products(
    db: AsyncSession,
    keyword: str | None = None,
    category: str | None = None,
) -> Sequence[QcProduct]:
    stmt: Select[tuple[QcProduct]] = select(QcProduct).where(_alive(QcProduct))
    if keyword:
        like = f"%{keyword.strip()}%"
        stmt = stmt.where(or_(QcProduct.name.ilike(like), QcProduct.abbr.ilike(like)))
    if category:
        stmt = stmt.where(QcProduct.category == category)
    stmt = stmt.order_by(QcProduct.created_at.desc())
    return (await db.execute(stmt)).scalars().all()


async def list_items(db: AsyncSession, product_id: uuid.UUID, only_enabled: bool = False) -> Sequence[QcItem]:
    stmt = select(QcItem).where(QcItem.product_id == product_id, _alive(QcItem))
    if only_enabled:
        stmt = stmt.where(QcItem.is_enabled.is_(True))
    stmt = stmt.order_by(QcItem.sort_order, QcItem.item_no)
    return (await db.execute(stmt)).scalars().all()


async def get_item(db: AsyncSession, item_id: uuid.UUID) -> QcItem | None:
    stmt = select(QcItem).where(QcItem.id == item_id, _alive(QcItem))
    return (await db.execute(stmt)).scalar_one_or_none()


async def count_batches_by_level(db: AsyncSession, product_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, dict[str, int]]:
    """按品种聚合各等级批次数（一次 GROUP BY，避免 N+1）。"""
    if not product_ids:
        return {}
    stmt = (
        select(QcBatch.product_id, QcBatch.level, func.count().label("cnt"))
        .where(QcBatch.product_id.in_(product_ids), _alive(QcBatch))
        .group_by(QcBatch.product_id, QcBatch.level)
    )
    result: dict[uuid.UUID, dict[str, int]] = {}
    for product_id, level, count in (await db.execute(stmt)).all():
        result.setdefault(product_id, {})[level] = int(count)
    return result


async def get_batches_page(
    db: AsyncSession,
    product_id: uuid.UUID,
    page: int,
    page_size: int,
    batch_no: str | None = None,
    level: str | None = None,
) -> tuple[list[QcBatch], int]:
    conditions = [QcBatch.product_id == product_id, _alive(QcBatch)]
    if batch_no:
        conditions.append(QcBatch.batch_no.ilike(f"%{batch_no.strip()}%"))
    if level:
        conditions.append(QcBatch.level == level)

    total_stmt = select(func.count()).select_from(QcBatch).where(and_(*conditions))
    total = int((await db.execute(total_stmt)).scalar_one())

    stmt = (
        select(QcBatch)
        .where(and_(*conditions))
        .order_by(QcBatch.batch_no)
        .offset(max(page - 1, 0) * page_size)
        .limit(page_size)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return list(rows), total


async def get_values_by_batch_ids(
    db: AsyncSession,
    batch_ids: Sequence[uuid.UUID],
) -> Sequence[QcValue]:
    if not batch_ids:
        return []
    stmt = select(QcValue).where(QcValue.batch_id.in_(batch_ids), _alive(QcValue))
    return (await db.execute(stmt)).scalars().all()


async def get_all_batches(db: AsyncSession, product_id: uuid.UUID) -> Sequence[QcBatch]:
    stmt = select(QcBatch).where(QcBatch.product_id == product_id, _alive(QcBatch))
    return (await db.execute(stmt)).scalars().all()


async def get_all_values(db: AsyncSession, product_id: uuid.UUID) -> Sequence[QcValue]:
    stmt = (
        select(QcValue)
        .join(QcBatch, QcBatch.id == QcValue.batch_id)
        .where(QcBatch.product_id == product_id, _alive(QcBatch), _alive(QcValue))
    )
    return (await db.execute(stmt)).scalars().all()


async def get_batch(db: AsyncSession, batch_id: uuid.UUID) -> QcBatch | None:
    stmt = select(QcBatch).where(QcBatch.id == batch_id, _alive(QcBatch))
    return (await db.execute(stmt)).scalar_one_or_none()


async def get_batch_by_no(db: AsyncSession, product_id: uuid.UUID, batch_no: str) -> QcBatch | None:
    stmt = select(QcBatch).where(
        QcBatch.product_id == product_id,
        QcBatch.batch_no == batch_no,
        _alive(QcBatch),
    )
    return (await db.execute(stmt)).scalar_one_or_none()


async def stats_by_level(db: AsyncSession, product_id: uuid.UUID) -> dict[str, int]:
    stmt = (
        select(QcBatch.level, func.count())
        .where(QcBatch.product_id == product_id, _alive(QcBatch))
        .group_by(QcBatch.level)
    )
    result: dict[str, int] = {}
    for level, count in (await db.execute(stmt)).all():
        result[str(level)] = int(count)
    return result


async def attention_batches(db: AsyncSession, limit: int = 20) -> list[tuple[QcBatch, str]]:
    """全品种异常批次，按风险排序（超法定 → 超内控 → 超趋势）。"""
    stmt = (
        select(QcBatch, QcProduct.name)
        .join(QcProduct, QcProduct.id == QcBatch.product_id)
        .where(
            _alive(QcBatch),
            _alive(QcProduct),
            QcBatch.level.in_([LEVEL_OOS, LEVEL_INTERNAL, LEVEL_TREND]),
        )
        # 用 CASE 而不是 array_position(ARRAY[...], col)：
        # 后者在 PostgreSQL 下无法推断参数化数组的元素类型，
        # 会抛 could not determine polymorphic type，接口直接 500。
        .order_by(
            case(
                (QcBatch.level == LEVEL_OOS, 1),
                (QcBatch.level == LEVEL_INTERNAL, 2),
                (QcBatch.level == LEVEL_TREND, 3),
                (QcBatch.level == LEVEL_NORMAL, 4),
                (QcBatch.level == LEVEL_SKIP, 5),
                else_=6,
            ),
            QcBatch.created_at.desc(),
        )
        .limit(limit)
    )
    return [(row[0], row[1]) for row in (await db.execute(stmt)).all()]


__all__ = [
    "attention_batches",
    "count_batches_by_level",
    "get_all_batches",
    "get_all_values",
    "get_batch",
    "get_batch_by_no",
    "get_batches_page",
    "get_item",
    "get_product",
    "get_product_by_abbr",
    "get_values_by_batch_ids",
    "list_items",
    "list_products",
    "stats_by_level",
]
