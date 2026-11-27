"""批次分页、手工录入、统计与「需关注批号」。"""

from __future__ import annotations

import logging
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from openpyxl.utils import get_column_letter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, NotFoundException
from app.modules.quality.qc_report.constants import (
    LEVEL_INTERNAL,
    LEVEL_NORMAL,
    LEVEL_OOS,
    LEVEL_PENDING,
    LEVEL_SKIP,
    LEVEL_TREND,
    SOURCE_IMPORT,
    SOURCE_MANUAL,
)
from app.modules.quality.qc_report.models import QcBatch, QcItem, QcValue
from app.modules.quality.qc_report.repository import (
    attention_batches,
    get_batch_by_no,
    get_batches_page,
    get_product,
    get_values_by_batch_ids,
    list_items,
    stats_by_level,
)
from app.modules.quality.qc_report.schemas import (
    QcAttentionBatch,
    QcBatchCreate,
    QcBatchPageData,
    QcBatchRow,
    QcStatsResponse,
)
from app.modules.quality.qc_report.service.judge import (
    JudgeItem,
    aggregate_level,
    compile_item_limits,
    judge_value,
)
from app.modules.quality.qc_report.service.xlsx_parser import ColumnHeader, parse_result_xlsx

logger = logging.getLogger(__name__)

_SKIP_LEVELS = (LEVEL_SKIP, LEVEL_PENDING)


def _assemble_row(
    batch: QcBatch,
    values: list[QcValue],
) -> QcBatchRow:
    return QcBatchRow(
        id=batch.id,
        batch_no=batch.batch_no,
        level=batch.level,
        note=batch.note,
        entered_by_name=batch.entered_by_name,
        source=batch.source,
        created_at=batch.created_at,
        values={str(value.item_id): value.actual_value for value in values},
        levels={str(value.item_id): value.level for value in values},
    )


async def list_batches(
    db: AsyncSession,
    product_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
    batch_no: str | None = None,
    level: str | None = None,
) -> QcBatchPageData:
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))

    page = max(page, 1)
    page_size = min(max(page_size, 1), 200)
    batches, total = await get_batches_page(db, product_id, page, page_size, batch_no, level)
    # 一次取回本页所有实测值，避免逐批查询
    values = await get_values_by_batch_ids(db, [batch.id for batch in batches])
    grouped: dict[uuid.UUID, list[QcValue]] = {}
    for value in values:
        grouped.setdefault(value.batch_id, []).append(value)

    return QcBatchPageData(
        total=total,
        page=page,
        page_size=page_size,
        items=[_assemble_row(batch, grouped.get(batch.id, [])) for batch in batches],
    )


def _build_batch(
    *,
    product_id: uuid.UUID,
    batch_no: str,
    items: list[QcItem],
    values: dict[str, str],
    note: str | None,
    source: str,
    user_id: uuid.UUID | None,
    user_name: str | None,
) -> tuple[QcBatch, list[QcValue]]:
    """组装一批的批次对象与逐项判定结果，不负责入库。

    手工录入与 Excel 批量导入共用，保证两条路径的判定口径完全一致。
    """
    batch = QcBatch(
        id=uuid.uuid4(),
        product_id=product_id,
        batch_no=batch_no,
        level=LEVEL_PENDING,
        note=note,
        entered_by_name=user_name,
        source=source,
        created_by=user_id,
        updated_by=user_id,
    )

    levels: list[str] = []
    created_values: list[QcValue] = []
    for item in items:
        judge_item = JudgeItem(
            item_name=item.item_name,
            value_type=item.value_type,
            legal_text=item.legal_text,
            internal_text=item.internal_text,
            sigma_text=item.sigma_text,
            is_record_only=item.is_record_only,
        )
        actual = values.get(str(item.id))
        if actual is not None:
            actual = actual.strip() or None
        result = judge_value(judge_item, actual, compile_item_limits(judge_item))
        levels.append(result.level)
        created_values.append(
            QcValue(
                id=uuid.uuid4(),
                batch_id=batch.id,
                item_id=item.id,
                actual_value=actual[:255] if actual else None,
                numeric_value=result.numeric_value,
                level=result.level,
                created_by=user_id,
                updated_by=user_id,
            )
        )

    batch.level = aggregate_level(levels)
    return batch, created_values


async def create_batch(
    db: AsyncSession,
    product_id: uuid.UUID,
    data: QcBatchCreate,
    user_id: uuid.UUID | None,
    user_name: str | None,
) -> QcBatchRow:
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))

    batch_no = data.batch_no.strip()
    if not batch_no:
        raise AppException(status_code=400, message="批号不能为空")
    if await get_batch_by_no(db, product_id, batch_no) is not None:
        raise AppException(status_code=409, message=f"批号 {batch_no} 已存在，同一品种内不能重复")

    items: list[QcItem] = [item for item in await list_items(db, product_id) if item.is_enabled]
    if not items:
        raise AppException(status_code=400, message="该品种还没有检验项目，请先导入标准表")

    batch, created_values = _build_batch(
        product_id=product_id,
        batch_no=batch_no,
        items=items,
        values=data.values,
        note=data.note,
        source=SOURCE_MANUAL,
        user_id=user_id,
        user_name=user_name,
    )
    db.add(batch)
    for value in created_values:
        db.add(value)

    product.last_inspected_at = datetime.now(UTC)
    await db.flush()

    logger.info(
        "qc_report batch created",
        extra={"product_id": str(product_id), "batch_no": batch_no, "level": batch.level},
    )
    return _assemble_row(batch, created_values)


@dataclass
class BatchImportResult:
    """Excel 批量导入的统计结果。"""

    created_count: int = 0
    skipped_count: int = 0
    skipped_batch_nos: list[str] = field(default_factory=list)
    level_counts: dict[str, int] = field(default_factory=dict)


def _normalize_header(text: str | None) -> str:
    """表头归一化：全角转半角、去掉换行与所有空白。"""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", text)
    for token in ("\n", "\r", " ", "\u3000"):
        normalized = normalized.replace(token, "")
    return normalized.strip()


def _validate_columns(columns: list[ColumnHeader], items: list[QcItem]) -> None:
    """文件列与系统项目必须一一对应，错位就拦下，避免数据串列。"""
    if len(columns) != len(items):
        if len(columns) < len(items):
            missing = items[len(columns)]
            letter = get_column_letter(missing.sort_order)
            raise AppException(
                status_code=400,
                message=(
                    f"系统有 {len(items)} 个检验项目，你的表只有 {len(columns)} 列，"
                    f"少了第 {len(columns) + 1} 个项目「{missing.item_name}」（列 {letter}）"
                ),
            )
        extra = columns[len(items)]
        raise AppException(
            status_code=400,
            message=(
                f"系统有 {len(items)} 个检验项目，你的表有 {len(columns)} 列，"
                f"多了第 {extra.index} 列「{extra.name}」（列 {extra.letter}）"
            ),
        )

    differences = [
        f"第 {column.index} 列 {column.letter}：表里是「{column.name}」，系统里是「{item.item_name}」"
        for column, item in zip(columns, items)
        if _normalize_header(column.name) != _normalize_header(item.item_name)
    ]
    if differences:
        shown = "；".join(differences[:3])
        more = f" 等 {len(differences)} 处" if len(differences) > 3 else ""
        raise AppException(status_code=400, message=f"表头与系统项目对不上：{shown}{more}")


async def _existing_batch_nos(db: AsyncSession, product_id: uuid.UUID) -> set[str]:
    """一次查出该品种已有批号，避免逐行查询。"""
    stmt = select(QcBatch.batch_no).where(QcBatch.product_id == product_id)
    return {row[0] for row in (await db.execute(stmt)).all()}


async def import_batches_from_xlsx(
    db: AsyncSession,
    product_id: uuid.UUID,
    content: bytes,
    *,
    user_id: uuid.UUID | None,
    user_name: str | None,
) -> BatchImportResult:
    """从结果表批量新增检验批次。

    列按位置对应（第 1 个数据列 → 第 1 个项目），因此列数或表头不一致时直接拒绝，
    绝不按名字猜；批号重复的行跳过，其余照常写入。
    """
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))

    try:
        sheet = parse_result_xlsx(content)
    except Exception as exc:  # noqa: BLE001 - 解析失败统一转成可读提示
        logger.warning("qc_report batch import parse failed: %s", exc)
        raise AppException(status_code=400, message="文件无法解析，请确认是检验结果表（.xlsx）") from exc

    items: list[QcItem] = [item for item in await list_items(db, product_id) if item.is_enabled]
    if not items:
        raise AppException(status_code=400, message="该品种还没有检验项目，请先导入标准表")

    columns = sorted(
        (header for header in sheet.headers if header.index != sheet.batch_column),
        key=lambda header: header.index,
    )
    _validate_columns(columns, items)

    existing = await _existing_batch_nos(db, product_id)
    result = BatchImportResult()

    for row in sheet.rows:
        batch_no = (row.batch_no or "").strip()
        if not batch_no:
            continue
        if batch_no in existing:
            result.skipped_count += 1
            result.skipped_batch_nos.append(batch_no)
            continue

        values: dict[str, str] = {}
        for position, column in enumerate(columns):
            raw = row.values.get(column.index)
            values[str(items[position].id)] = raw if raw is not None else ""

        batch, created_values = _build_batch(
            product_id=product_id,
            batch_no=batch_no,
            items=items,
            values=values,
            note=None,
            source=SOURCE_IMPORT,
            user_id=user_id,
            user_name=user_name,
        )
        db.add(batch)
        for value in created_values:
            db.add(value)

        existing.add(batch_no)
        result.created_count += 1
        result.level_counts[batch.level] = result.level_counts.get(batch.level, 0) + 1

    product.last_inspected_at = datetime.now(UTC)
    await db.flush()

    logger.info(
        "qc_report batches imported",
        extra={
            "product_id": str(product_id),
            "created_count": result.created_count,
            "skipped_count": result.skipped_count,
        },
    )
    return result


async def get_stats(db: AsyncSession, product_id: uuid.UUID) -> QcStatsResponse:
    product = await get_product(db, product_id)
    if product is None:
        raise NotFoundException("品种", str(product_id))

    counts = await stats_by_level(db, product_id)
    return QcStatsResponse(
        total=sum(counts.values()),
        oos=counts.get(LEVEL_OOS, 0),
        internal=counts.get(LEVEL_INTERNAL, 0),
        trend=counts.get(LEVEL_TREND, 0),
        normal=counts.get(LEVEL_NORMAL, 0),
        skip=counts.get(LEVEL_SKIP, 0),
        pending=counts.get(LEVEL_PENDING, 0),
    )


async def get_attention_batches(db: AsyncSession, limit: int = 20) -> list[QcAttentionBatch]:
    rows = await attention_batches(db, limit=limit)
    result: list[QcAttentionBatch] = []
    for batch, product_name in rows:
        result.append(
            QcAttentionBatch(
                product_id=batch.product_id,
                product_name=product_name,
                batch_id=batch.id,
                batch_no=batch.batch_no,
                level=batch.level,
                reason=_reason_text(batch.level),
            )
        )
    return result


def _reason_text(level: str) -> str:
    mapping = {
        LEVEL_OOS: "存在超法定项目，按 OOS 程序调查",
        LEVEL_INTERNAL: "超出企业内控标准",
        LEVEL_TREND: "超出 3σ 趋势限",
        LEVEL_NORMAL: "全部在限内",
        LEVEL_SKIP: "仅记录",
        LEVEL_PENDING: "待检",
    }
    return mapping.get(level, level)


__all__ = ["create_batch", "get_attention_batches", "get_stats", "list_batches"]
