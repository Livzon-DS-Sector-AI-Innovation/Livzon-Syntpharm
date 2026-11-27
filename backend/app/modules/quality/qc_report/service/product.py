"""品种与检验项目的业务逻辑，以及标准变更后的整体重判。"""

from __future__ import annotations

import logging
import math
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import cast

from sqlalchemy import Table, bindparam, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.modules.quality.qc_report.constants import (
    LEVEL_INTERNAL,
    LEVEL_NORMAL,
    LEVEL_OOS,
    LEVEL_PENDING,
    LEVEL_SKIP,
    LEVEL_TREND,
)
from app.modules.quality.qc_report.models import QcBatch, QcItem, QcProduct, QcValue
from app.modules.quality.qc_report.repository import (
    count_batches_by_level,
    get_all_batches,
    get_all_values,
    get_item,
    get_product,
    get_product_by_abbr,
    list_items,
    list_products,
)
from app.modules.quality.qc_report.schemas import (
    QcItemResponse,
    QcItemUpdate,
    QcProductCreate,
    QcProductListItem,
    QcProductResponse,
    QcProductUpdate,
    QcRejudgeResponse,
)
from app.modules.quality.qc_report.service.judge import (
    JudgeItem,
    aggregate_level,
    compile_item_limits,
    judge_value,
)
from app.modules.quality.qc_report.service.limits import infer_value_type, normalize_standard_text

logger = logging.getLogger(__name__)

# 合格率口径：正常批次 / 有结论的批次（待检不计入分母）
_GRADED_LEVELS = (LEVEL_NORMAL, LEVEL_TREND, LEVEL_INTERNAL, LEVEL_OOS)


def _to_item_response(item: QcItem) -> QcItemResponse:
    return QcItemResponse(
        id=item.id,
        product_id=item.product_id,
        item_no=item.item_no,
        item_name=item.item_name,
        standard_item_name=item.standard_item_name,
        column_group_start=item.column_group_start,
        sub_label=item.sub_label,
        value_type=item.value_type,
        unit=item.unit,
        legal_text=item.legal_text,
        internal_text=item.internal_text,
        sigma_text=item.sigma_text,
        source_column=item.source_column,
        is_record_only=item.is_record_only,
        sigma_basis_period=item.sigma_basis_period,
        sigma_updated_by=item.sigma_updated_by,
        sigma_updated_at=item.sigma_updated_at,
        sort_order=item.sort_order,
        is_enabled=item.is_enabled,
    )


def to_product_response(product: QcProduct) -> QcProductResponse:
    return QcProductResponse(
        id=product.id,
        name=product.name,
        abbr=product.abbr,
        category=product.category,
        quality_standard=product.quality_standard,
        source_file_name=product.source_file_name,
        status=product.status,
        last_inspected_at=product.last_inspected_at,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


async def create_product(db: AsyncSession, data: QcProductCreate, user_id: uuid.UUID | None) -> QcProductResponse:
    existing = await get_product_by_abbr(db, data.abbr)
    if existing is not None:
        raise AppException(status_code=409, message=f"品名缩写 {data.abbr.upper()} 已被「{existing.name}」占用")
    product = QcProduct(
        id=uuid.uuid4(),
        name=data.name.strip(),
        abbr=data.abbr.strip().upper(),
        category=data.category,
        quality_standard=data.quality_standard,
        status=data.status,
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(product)
    await db.flush()
    return to_product_response(product)


async def update_product(
    db: AsyncSession,
    product_id: uuid.UUID,
    data: QcProductUpdate,
    user_id: uuid.UUID | None,
) -> QcProductResponse:
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))

    if data.abbr is not None:
        new_abbr = data.abbr.strip().upper()
        if new_abbr != product.abbr:
            occupied = await get_product_by_abbr(db, new_abbr)
            if occupied is not None and occupied.id != product.id:
                raise AppException(status_code=409, message=f"品名缩写 {new_abbr} 已被「{occupied.name}」占用")
            product.abbr = new_abbr
    if data.name is not None:
        product.name = data.name.strip()
    if data.category is not None:
        product.category = data.category
    if data.quality_standard is not None:
        product.quality_standard = data.quality_standard
    if data.status is not None:
        product.status = data.status
    product.updated_by = user_id
    await db.flush()
    return to_product_response(product)


async def delete_product(db: AsyncSession, product_id: uuid.UUID, user_id: uuid.UUID | None) -> None:
    """软删除品种，并联动软删项目、批次与实测值（应用层，不用数据库级联）。"""
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))

    now = datetime.now(UTC)
    product.is_deleted = True
    product.updated_by = user_id

    batches = await get_all_batches(db, product_id)
    batch_ids = [batch.id for batch in batches]
    items = await list_items(db, product_id)

    if batch_ids:
        await db.execute(
            update(QcValue)
            .where(QcValue.batch_id.in_(batch_ids), QcValue.is_deleted.is_(False))
            .values(is_deleted=True, updated_by=user_id, updated_at=now)
        )
        await db.execute(
            update(QcBatch)
            .where(QcBatch.id.in_(batch_ids), QcBatch.is_deleted.is_(False))
            .values(is_deleted=True, updated_by=user_id, updated_at=now)
        )
    if items:
        await db.execute(
            update(QcItem)
            .where(QcItem.product_id == product_id, QcItem.is_deleted.is_(False))
            .values(is_deleted=True, updated_by=user_id, updated_at=now)
        )
    await db.flush()


async def list_products_with_stats(
    db: AsyncSession,
    keyword: str | None = None,
    category: str | None = None,
    top_level: str | None = None,
) -> list[QcProductListItem]:
    products = await list_products(db, keyword=keyword, category=category)
    if not products:
        return []

    stats = await count_batches_by_level(db, [product.id for product in products])
    result: list[QcProductListItem] = []
    for product in products:
        level_counts = stats.get(product.id, {})
        total = sum(level_counts.values())
        graded = sum(level_counts.get(level, 0) for level in _GRADED_LEVELS)
        normal = level_counts.get(LEVEL_NORMAL, 0)
        top = _top_level(level_counts, total)
        item = QcProductListItem(
            id=product.id,
            name=product.name,
            abbr=product.abbr,
            category=product.category,
            quality_standard=product.quality_standard,
            status=product.status,
            last_inspected_at=product.last_inspected_at,
            batch_count=total,
            normal_count=normal,
            oos_count=level_counts.get(LEVEL_OOS, 0),
            internal_count=level_counts.get(LEVEL_INTERNAL, 0),
            trend_count=level_counts.get(LEVEL_TREND, 0),
            pending_count=level_counts.get(LEVEL_PENDING, 0),
            pass_rate=round(normal / graded * 100, 1) if graded else 0.0,
            top_level=top,
        )
        if top_level and item.top_level != top_level:
            continue
        result.append(item)
    return result


def _top_level(level_counts: dict[str, int], total: int) -> str:
    if total == 0:
        return LEVEL_PENDING
    for level in (LEVEL_OOS, LEVEL_INTERNAL, LEVEL_TREND, LEVEL_NORMAL):
        if level_counts.get(level):
            return level
    return LEVEL_SKIP if level_counts.get(LEVEL_SKIP) else LEVEL_PENDING


async def get_items(db: AsyncSession, product_id: uuid.UUID) -> list[QcItemResponse]:
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))
    items = await list_items(db, product_id)
    return [_to_item_response(item) for item in items]


async def update_item(
    db: AsyncSession,
    item_id: uuid.UUID,
    data: QcItemUpdate,
    user_id: uuid.UUID | None,
) -> QcItemResponse:
    item = await get_item(db, item_id)
    if item is None:
        raise NotFoundException("检验项目", str(item_id))

    # 手工改的标准也走同一套归一化，避免倒着写的区间进库
    if data.legal_text is not None:
        item.legal_text = normalize_standard_text(data.legal_text) or None
    if data.internal_text is not None:
        item.internal_text = normalize_standard_text(data.internal_text) or None
    if data.sigma_text is not None:
        item.sigma_text = normalize_standard_text(data.sigma_text) or None
        item.sigma_updated_by = user_id
        item.sigma_updated_at = datetime.now(UTC)
    if data.sigma_basis_period is not None:
        item.sigma_basis_period = data.sigma_basis_period or None
    if data.is_enabled is not None:
        item.is_enabled = data.is_enabled

    # 标准变了，项目类型可能从文字变成数值，重新推断
    item.value_type = infer_value_type(item.legal_text, item.internal_text, item.sigma_text)
    item.updated_by = user_id
    await db.flush()
    return _to_item_response(item)


def _same_number(left: float | None, right: object | None) -> bool:
    """数值比较：忽略 Decimal / float 的类型差异。"""
    if left is None or right is None:
        return left is None and right is None
    try:
        return math.isclose(float(left), float(str(right)), rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return False


async def rejudge_product(
    db: AsyncSession,
    product_id: uuid.UUID,
    user_id: uuid.UUID | None,
) -> QcRejudgeResponse:
    """标准或 3σ 修改后，按新标准重算全部批次的等级。"""
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))

    items = [item for item in await list_items(db, product_id) if item.is_enabled]
    if not items:
        return QcRejudgeResponse(product_id=product_id, batch_count=0, value_count=0, changed_batch_count=0)

    judge_items = {
        item.id: JudgeItem(
            item_name=item.item_name,
            value_type=item.value_type,
            legal_text=item.legal_text,
            internal_text=item.internal_text,
            sigma_text=item.sigma_text,
            is_record_only=item.is_record_only,
        )
        for item in items
    }
    limits = {item_id: compile_item_limits(judge_item) for item_id, judge_item in judge_items.items()}

    batches = await get_all_batches(db, product_id)
    values = await get_all_values(db, product_id)

    batch_levels: dict[uuid.UUID, list[str]] = {}
    value_updates: list[dict[str, object]] = []
    changed_values = 0
    # 只要某个单元格的等级变了，它所在的批次就算「有变化」。
    # 只看批次整体等级会漏报：批次原本就是超法定时，某个项目从正常变超趋势
    # 不会改变整体等级，用户却明明看到格子变黄了。
    changed_batch_ids: set[uuid.UUID] = set()
    for value in values:
        judge_item = judge_items.get(value.item_id)
        if judge_item is None:
            continue
        result = judge_value(judge_item, value.actual_value, limits[value.item_id])
        batch_levels.setdefault(value.batch_id, []).append(result.level)
        # 库里 numeric_value 是 Decimal、判定返回 float，直接比较会恒为真，
        # 导致每次重判都误报「全部变化」。统一转 float 再比。
        if result.level != value.level or not _same_number(result.numeric_value, value.numeric_value):
            changed_values += 1
            changed_batch_ids.add(value.batch_id)
            value_updates.append({"b_id": value.id, "b_level": result.level, "b_num": result.numeric_value})

    if value_updates:
        value_table = cast(Table, QcValue.__table__)
        await db.execute(
            update(value_table)
            .where(value_table.c.id == bindparam("b_id"))
            .values(level=bindparam("b_level"), numeric_value=bindparam("b_num")),
            value_updates,
        )

    batch_updates: list[dict[str, object]] = []
    for batch in batches:
        new_level = aggregate_level(batch_levels.get(batch.id, []))
        if new_level != batch.level:
            batch_updates.append({"b_id": batch.id, "b_level": new_level})
    if batch_updates:
        batch_table = cast(Table, QcBatch.__table__)
        await db.execute(
            update(batch_table).where(batch_table.c.id == bindparam("b_id")).values(level=bindparam("b_level")),
            batch_updates,
        )

    await db.flush()
    logger.info(
        "qc_report rejudged",
        extra={
            "product_id": str(product_id),
            "value_count": len(values),
            "changed_values": changed_values,
            "changed_batches": len(changed_batch_ids),
        },
    )
    return QcRejudgeResponse(
        product_id=product_id,
        batch_count=len(batches),
        value_count=len(values),
        changed_batch_count=len(changed_batch_ids),
        changed_value_count=changed_values,
    )


async def get_saved_mapping(db: AsyncSession, product_id: uuid.UUID) -> dict[str, str]:
    """读取历史映射（项目名 → 列名），供再次导入时自动套用。"""
    items: Sequence[QcItem] = await list_items(db, product_id)
    return {item.item_name: item.source_column for item in items if item.source_column and not item.is_record_only}


__all__ = [
    "to_product_response",
    "create_product",
    "delete_product",
    "get_items",
    "get_saved_mapping",
    "list_products_with_stats",
    "rejudge_product",
    "update_item",
    "update_product",
]
