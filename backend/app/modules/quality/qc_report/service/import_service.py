"""质量检验台账导入：解析预览 + 事务入库。

两阶段设计：
- `preview_import` 只解析、不写库，返回项目清单与映射建议供人工确认
- `commit_import` 携带人工指认结果再次解析，在一个事务里写品种/项目/批次/值

不落中间态（不建草稿表、不写临时文件），重解析成本约 1 秒，换来零残留。
"""

from __future__ import annotations

import logging
import re
import uuid
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.modules.quality.qc_report.constants import (
    SOURCE_IMPORT,
    VALUE_TYPE_GRADE,
    VALUE_TYPE_QUAL,
    VALUE_TYPE_QUANT,
)
from app.modules.quality.qc_report.models import QcBatch, QcItem, QcProduct, QcValue
from app.modules.quality.qc_report.schemas import (
    QcImportCommitResponse,
    QcImportExtraColumn,
    QcImportPreviewItem,
    QcImportPreviewResponse,
    QcImportSummary,
    QcStandardConflict,
    QcStandardSourceItem,
    QcUnmatchedCandidate,
    QcUnmatchedItem,
)
from app.modules.quality.qc_report.service.bridge import bridge_items
from app.modules.quality.qc_report.service.docx_parser import (
    DocxParseError,
    ParsedStandard,
    ParsedStandardItem,
    parse_standard_docx,
)
from app.modules.quality.qc_report.service.judge import (
    ItemLimits,
    JudgeItem,
    aggregate_level,
    compile_item_limits,
    judge_value,
)
from app.modules.quality.qc_report.service.limits import (
    infer_value_type,
    is_empty_standard,
    normalize_standard_text,
    parse_limit,
)
from app.modules.quality.qc_report.service.standards import (
    LAYER_LABELS,
    LAYERS,
    SEVERITY_NUMERIC,
    SEVERITY_TEXT,
    SOURCE_DOCX,
    SOURCE_EXCEL,
    SOURCE_NONE,
    STATUS_DIFF,
    STATUS_ONLY_DOCX,
    LayerComparison,
    compare_item_layers,
    compare_standard,
    is_single_value_text,
    resolve_layer,
    summarize,
)
from app.modules.quality.qc_report.service.xlsx_parser import (
    ColumnHeader,
    ParsedSheet,
    XlsxParseError,
    parse_result_xlsx,
)

logger = logging.getLogger(__name__)

MAX_FILE_BYTES = 10 * 1024 * 1024
_BATCH_CHUNK = 2000
_VALUE_CHUNK = 2000

_SUFFIXES = ("质量报表", "质量标准", "检验报表", "检验数据", "检验台账", "台账", "报表", "标准", "数据")


def _ensure_size(content: bytes, file_name: str) -> None:
    if not content:
        raise AppException(status_code=400, message=f"文件 {file_name} 是空的")
    if len(content) > MAX_FILE_BYTES:
        raise AppException(status_code=400, message=f"文件 {file_name} 超过 10MB 限制")


def suggest_from_filename(file_name: str) -> tuple[str, str]:
    """从文件名推断品种名与缩写，如「头孢曲松钠质量报表（CHP）.xlsx」→ (头孢曲松钠, CHP)。"""
    stem = Path(file_name).stem
    abbr = ""
    match = re.search(r"[（(]\s*([A-Za-z0-9]{2,8})\s*[）)]", stem)
    if match:
        abbr = match.group(1).upper()
    product_name = re.sub(r"[（(][^）)]*[）)]", "", stem)
    for suffix in _SUFFIXES:
        product_name = product_name.replace(suffix, "")
    product_name = product_name.strip() or stem
    return product_name, abbr


def _parse_both(
    docx_bytes: bytes, docx_name: str, xlsx_bytes: bytes, xlsx_name: str
) -> tuple[ParsedStandard, ParsedSheet]:
    _ensure_size(docx_bytes, docx_name)
    _ensure_size(xlsx_bytes, xlsx_name)
    try:
        standard = parse_standard_docx(docx_bytes)
    except DocxParseError as exc:
        raise AppException(status_code=400, message=f"标准表解析失败：{exc}") from exc
    try:
        sheet = parse_result_xlsx(xlsx_bytes)
    except XlsxParseError as exc:
        raise AppException(status_code=400, message=f"结果表解析失败：{exc}") from exc
    return standard, sheet


def _is_unrecognized(item: ParsedStandardItem) -> bool:
    """三层标准都解析不出数值、又不是明显的文字/等级型 → 需要人工补。"""
    texts = [t for t in (item.legal_text, item.internal_text, item.sigma_text) if t]
    if not texts:
        return False
    if any(parse_limit(text).is_active for text in texts):
        return False
    value_type = infer_value_type(item.legal_text, item.internal_text, item.sigma_text)
    if value_type in (VALUE_TYPE_GRADE, VALUE_TYPE_QUAL):
        return False
    return True


def _build_preview(
    standard: ParsedStandard,
    sheet: ParsedSheet,
    saved_mapping: dict[str, str] | None = None,
    manual_mapping: dict[str, str] | None = None,
) -> tuple[
    list[QcImportPreviewItem],
    list[QcImportExtraColumn],
    list[str],
    list[QcStandardConflict],
    list[QcUnmatchedItem],
    QcImportSummary,
]:
    """按结果表的列逐列比对两份文件的三层标准。

    `manual_mapping` 是本次人工指定的「项目名 -> 列字母」，优先于历史映射。
    """
    columns = [header for header in sheet.headers if header.index != sheet.batch_column]
    item_names = [item.item_name for item in standard.items]
    docx_by_name = {item.item_name: item for item in standard.items}
    letter_by_index = {column.index: column.letter for column in columns}

    # 1) 基准：不含本次人工指定，确定「本来就需要人工对应」的项目。
    #    这份清单是固定的，不会因为用户选了某个列就少一行（否则选错了没法改）。
    base_bridge = bridge_items(item_names, columns, saved_mapping or {})
    base_pending = {match.item_name for match in base_bridge.pending}

    # 2) 当前：含本次人工指定，用于取每一项现在落到了哪一列
    merged_mapping: dict[str, str] = dict(saved_mapping or {})
    merged_mapping.update(manual_mapping or {})
    bridge = bridge_items(item_names, columns, merged_mapping)
    auto_by_name = {match.item_name: match for match in bridge.auto}
    col_to_docx_name = {match.column_index: match.item_name for match in bridge.auto}
    unmatched_docx = [match.item_name for match in bridge.pending]

    # 待对应清单 = 基准 ∪ 当前（含「被挤掉」的项目），按标准表项目顺序稳定输出
    target_names = [name for name in item_names if name in (base_pending | set(unmatched_docx))]
    # 候选给全部数据列：已对应的要能回显，也要能改到别的列
    full_candidates = [
        QcUnmatchedCandidate(letter=column.letter, name=column.name)
        for column in sorted(columns, key=lambda item: item.index)
    ]

    unmatched_items: list[QcUnmatchedItem] = []
    for name in target_names:
        docx_item = docx_by_name.get(name)
        matched = auto_by_name.get(name)
        unmatched_items.append(
            QcUnmatchedItem(
                item_name=name,
                candidates=full_candidates,
                docx_legal_text=docx_item.legal_text if docx_item else None,
                docx_internal_text=docx_item.internal_text if docx_item else None,
                docx_sigma_text=docx_item.sigma_text if docx_item else None,
                matched_column_letter=letter_by_index.get(matched.column_index) if matched else None,
                matched_column_name=matched.column_name if matched else None,
            )
        )

    # 仅当基准桥接里连候选列都没有时才算真的跳过（结果表确实缺这一列）
    skipped_items = [match.item_name for match in base_bridge.pending if not match.candidates]

    comparisons: list[LayerComparison] = []
    preview_items: list[QcImportPreviewItem] = []
    unrecognized: list[str] = []

    for column in sorted(columns, key=lambda item: item.index):
        docx_name = col_to_docx_name.get(column.index)
        docx_item = docx_by_name.get(docx_name) if docx_name else None
        excel_layers = {
            "legal": column.legal_text,
            "internal": column.internal_text,
            "sigma": column.sigma_text,
        }
        docx_layers = (
            {
                "legal": docx_item.legal_text,
                "internal": docx_item.internal_text,
                "sigma": docx_item.sigma_text,
            }
            if docx_item is not None
            else None
        )
        item_comparisons = compare_item_layers(
            column_index=column.index,
            column_letter=column.letter,
            item_name=column.name,
            excel_layers=excel_layers,
            docx_layers=docx_layers,
        )
        comparisons.extend(item_comparisons)

        statuses = {comparison.status for comparison in item_comparisons}
        if docx_item is None:
            # 标准表里没对上这一列，需要人工指一次或按「仅结果表有」处理
            match_kind = "pending" if unmatched_docx else "only_excel"
        elif STATUS_DIFF in statuses:
            match_kind = "diff"
        else:
            match_kind = "same"

        preview_items.append(
            QcImportPreviewItem(
                item_no=column.index,
                item_name=column.name,
                value_type=infer_value_type(column.legal_text, column.internal_text, column.sigma_text),
                unit=None,
                legal_text=column.legal_text,
                internal_text=column.internal_text,
                sigma_text=column.sigma_text,
                matched_column=docx_name,
                match_kind=match_kind,
                candidates=unmatched_docx if docx_item is None else [],
            )
        )
        if docx_item is not None and _is_unrecognized(docx_item):
            unrecognized.append(docx_item.item_name)

    conflicts = [
        QcStandardConflict(
            column_index=comparison.column_index,
            column_letter=comparison.column_letter,
            item_name=comparison.item_name,
            layer=comparison.layer,
            layer_label=comparison.layer_label,
            excel_text=comparison.excel_text,
            docx_text=comparison.docx_text,
            note=comparison.note,
            severity=comparison.severity or SEVERITY_TEXT,
        )
        for comparison in comparisons
        if comparison.status == STATUS_DIFF
    ]
    summary = QcImportSummary(
        **summarize(
            comparisons,
            total_columns=len(columns),
            skipped_docx_items=skipped_items,
        )
    )
    extra = [
        QcImportExtraColumn(column_index=item.item_no, column_name=item.item_name)
        for item in preview_items
        if item.match_kind in ("pending", "only_excel")
    ]
    return preview_items, extra, unrecognized, conflicts, unmatched_items, summary


def _sample_values(sheet: ParsedSheet, limit: int = 3) -> list[dict[str, str | None]]:
    samples: list[dict[str, str | None]] = []
    for row in sheet.rows[:limit]:
        record: dict[str, str | None] = {"批号": row.batch_no}
        for header in sheet.headers:
            if header.index == sheet.batch_column:
                continue
            record[header.name] = row.values.get(header.index)
        samples.append(record)
    return samples


def preview_import(
    docx_bytes: bytes,
    docx_name: str,
    xlsx_bytes: bytes,
    xlsx_name: str,
    saved_mapping: dict[str, str] | None = None,
    manual_mapping: dict[str, str] | None = None,
) -> QcImportPreviewResponse:
    """解析两个文件，返回项目清单与待指定项（不写库）。

    `manual_mapping` 让前端在选完对应关系后重新核对，无需重新上传文件。
    """
    standard, sheet = _parse_both(docx_bytes, docx_name, xlsx_bytes, xlsx_name)
    preview_items, extra, unrecognized, conflicts, unmatched_items, summary = _build_preview(
        standard, sheet, saved_mapping, manual_mapping
    )
    product_name, abbr = suggest_from_filename(xlsx_name or docx_name)

    logger.info(
        "qc_report import preview",
        extra={
            "column_count": len(preview_items),
            "conflicts": len(conflicts),
            "batch_count": len(sheet.rows),
        },
    )
    return QcImportPreviewResponse(
        docx_file_name=docx_name,
        xlsx_file_name=xlsx_name,
        sheet_title=sheet.sheet_title,
        batch_count=len(sheet.rows),
        data_start_row=sheet.data_start_row,
        column_count=len(sheet.headers),
        product_name_suggestion=product_name,
        abbr_suggestion=abbr,
        quality_standard_suggestion=None,
        items=preview_items,
        extra_columns=extra,
        batch_no_samples=[row.batch_no for row in sheet.rows[:5]],
        sample_values=_sample_values(sheet),
        unrecognized_items=unrecognized,
        conflicts=conflicts,
        unmatched_items=unmatched_items,
        summary=summary,
    )


def _resolve_column_by_item(
    standard: ParsedStandard,
    sheet: ParsedSheet,
    manual_mapping: dict[str, str],
    saved_mapping: dict[str, str] | None,
) -> dict[str, int]:
    """最终的项目名 → 列号映射（人工指认优先，其次自动匹配）。"""
    columns = [header for header in sheet.headers if header.index != sheet.batch_column]
    by_name = {header.name: header.index for header in columns}
    merged_mapping: dict[str, str] = {}
    if saved_mapping:
        merged_mapping.update(saved_mapping)
    merged_mapping.update(manual_mapping or {})

    bridge = bridge_items([item.item_name for item in standard.items], columns, merged_mapping)
    resolved: dict[str, int] = {match.item_name: match.column_index for match in bridge.auto}
    for item_name, column_name in manual_mapping.items():
        if column_name in by_name:
            resolved[item_name] = by_name[column_name]
    return resolved


def _collect_unresolved(
    columns: list[ColumnHeader],
    column_to_docx: dict[int, ParsedStandardItem],
    resolutions: dict[str, str],
) -> list[str]:
    """列出仍未被人工裁决的**数值**冲突（形如 `K·法定标准`）。

    只拦数值范围不同的；文字表述不同默认采用结果表的值，不阻塞导入。
    """
    unresolved: list[str] = []
    for header in columns:
        std_item = column_to_docx.get(header.index)
        for layer in LAYERS:
            if f"{header.index}|{layer}" in resolutions:
                continue
            excel_text = getattr(header, f"{layer}_text", None)
            docx_text = getattr(std_item, f"{layer}_text", None) if std_item is not None else None
            comparison = compare_standard(excel_text, docx_text)
            if comparison.status == STATUS_DIFF and comparison.severity == SEVERITY_NUMERIC:
                unresolved.append(f"{header.letter}·{LAYER_LABELS[layer]}")
    return unresolved


def _chunks(items: list[dict[str, object]], size: int) -> Iterable[list[dict[str, object]]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]


@dataclass
class PreparedImport:
    """解析与校验后的中间结果，此时尚未写库。"""

    product_id: uuid.UUID
    product_name: str
    abbr: str
    category: str
    quality_standard: str | None
    docx_name: str
    xlsx_name: str
    sheet: ParsedSheet
    item_rows: list[dict[str, object]]
    judge_items: list[_ItemContext]
    skipped_standard_items: list[str]
    record_only_count: int
    resolved_conflicts: int
    unrecognized_items: list[str]
    standard_sources: list[QcStandardSourceItem]


ProgressCallback = Callable[[dict[str, object]], Awaitable[None]]


def prepare_import(
    *,
    docx_bytes: bytes,
    docx_name: str,
    xlsx_bytes: bytes,
    xlsx_name: str,
    name: str,
    abbr: str,
    category: str,
    quality_standard: str | None,
    manual_mapping: dict[str, str] | None = None,
    saved_mapping: dict[str, str] | None = None,
    resolutions: dict[str, str] | None = None,
) -> PreparedImport:
    """解析两份文件、比对标准、校验冲突、构建待写入行；全程不碰数据库。

    流式响应一旦开始就改不了状态码，所以所有可能报错的校验都放在这里：
    未裁决的数值冲突在这里抛 409，仍走全局异常处理。
    """
    abbr = abbr.strip().upper()
    if not abbr:
        raise AppException(status_code=400, message="品名缩写不能为空")
    # 质量标准是必填项：没有它，台账上这一行就是「未填写质量标准」，无法追溯依据
    if not (quality_standard or "").strip():
        raise AppException(status_code=400, message="质量标准不能为空，例如 ChP 2025 / QS-C011014-08")

    standard, sheet = _parse_both(docx_bytes, docx_name, xlsx_bytes, xlsx_name)
    resolved_columns = _resolve_column_by_item(standard, sheet, manual_mapping or {}, saved_mapping)
    columns = [header for header in sheet.headers if header.index != sheet.batch_column]

    # 先把「标准表项目 → 结果表列」定下来，供比对与取值共用
    std_by_name = {item.item_name: item for item in standard.items}
    column_to_docx: dict[int, ParsedStandardItem] = {}
    skipped_standard_items: list[str] = []
    for std_name, column_index in resolved_columns.items():
        std_item = std_by_name.get(std_name)
        if std_item is None:
            continue
        if column_index in column_to_docx:
            # 两项抢同一列：只留先到的，另一项按「未对应」提示
            skipped_standard_items.append(std_name)
            continue
        column_to_docx[column_index] = std_item
    for std_item in standard.items:
        if std_item.item_name not in resolved_columns:
            skipped_standard_items.append(std_item.item_name)

    # 有未裁决的数值冲突就不入库，避免系统替人做质量判断
    choices = resolutions or {}
    unresolved = _collect_unresolved(columns, column_to_docx, choices)
    if unresolved:
        raise AppException(
            status_code=409,
            message=(f"还有 {len(unresolved)} 处标准两份文件写得不一样，请先逐条确认：" + "、".join(unresolved[:6])),
        )

    product_id = uuid.uuid4()
    item_rows: list[dict[str, object]] = []
    judge_items: list[_ItemContext] = []
    record_only_count = 0
    resolved_conflicts = 0
    standard_sources: list[QcStandardSourceItem] = []

    # ── 项目：严格按 Excel 物理列序，一列一项 ──
    # 三层标准逐列比对两份文件：一致即采用，不一致按人工选择（resolutions）落地；
    # 单值标准（如吸收系数内控的 517）构不成范围，按「没写」存空。
    for header in sorted(columns, key=lambda column: column.index):
        std_item = column_to_docx.get(header.index)
        item_id = uuid.uuid4()
        layer_texts: dict[str, str | None] = {}
        layer_sources: set[str] = set()

        for layer in LAYERS:
            excel_text = getattr(header, f"{layer}_text", None)
            docx_text = getattr(std_item, f"{layer}_text", None) if std_item is not None else None
            choice = choices.get(f"{header.index}|{layer}")
            comparison = compare_standard(excel_text, docx_text)
            if choice:
                final_text, source = resolve_layer(excel_text, docx_text, choice)
                resolved_conflicts += 1
            elif comparison.status == STATUS_ONLY_DOCX:
                final_text, source = docx_text, SOURCE_DOCX
            else:
                final_text, source = excel_text, SOURCE_EXCEL
            # 单值（如 517）构不成范围；`/`、`未作规定` 等本就是「没有标准」，
            # 两种都存空，避免它们被当成有效阈值参与判定。
            if is_single_value_text(final_text) or is_empty_standard(final_text):
                final_text, source = None, SOURCE_NONE

            # 摆正反向书写的区间（0.5～0.0 → 0.0～0.5），只改写法不改判定
            final_text = normalize_standard_text(final_text)

            # 只记录「两份文件确实不一致」的层，供导入完成页核对：
            # 用户能在那里确认自己选的到底是标准表还是结果表
            if comparison.status == STATUS_DIFF:
                standard_sources.append(
                    QcStandardSourceItem(
                        column_letter=header.letter,
                        item_name=header.name,
                        layer=layer,
                        layer_label=LAYER_LABELS.get(layer, layer),
                        final_text=final_text,
                        source=source,
                        from_choice=bool(choice),
                    )
                )

            layer_texts[layer] = final_text
            if final_text:
                layer_sources.add(source)

        legal_text = layer_texts["legal"]
        internal_text = layer_texts["internal"]
        sigma_text = layer_texts["sigma"]
        if not layer_sources:
            standard_source: str | None = None
        elif len(layer_sources) == 1:
            standard_source = next(iter(layer_sources))
        else:
            standard_source = "mixed"

        has_standard = any(layer_texts.values())
        is_record_only = not has_standard
        value_type = infer_value_type(legal_text, internal_text, sigma_text) if has_standard else VALUE_TYPE_QUANT
        unit = std_item.unit if std_item is not None else None
        if is_record_only:
            record_only_count += 1

        item_rows.append(
            {
                "id": item_id,
                "product_id": product_id,
                "item_no": header.index,
                "item_name": header.name,
                "standard_item_name": std_item.item_name if std_item is not None else None,
                "standard_source": standard_source,
                "column_group_start": header.group_start or header.index,
                "sub_label": header.sub_label,
                "value_type": value_type,
                "unit": unit,
                "legal_text": legal_text,
                "internal_text": internal_text,
                "sigma_text": sigma_text,
                "source_column": header.name,
                "is_record_only": is_record_only,
                "sort_order": header.index,
                "is_enabled": True,
                "created_by": None,
                "updated_by": None,
            }
        )
        judge_items.append(
            _ItemContext(
                item_id=item_id,
                column_index=header.index,
                judge=JudgeItem(
                    item_name=header.name,
                    value_type=value_type,
                    legal_text=legal_text,
                    internal_text=internal_text,
                    sigma_text=sigma_text,
                    is_record_only=is_record_only,
                ),
            )
        )

    unrecognized = [item.item_name for item in standard.items if _is_unrecognized(item)]
    return PreparedImport(
        product_id=product_id,
        product_name=name.strip(),
        abbr=abbr,
        category=category,
        quality_standard=quality_standard,
        docx_name=docx_name,
        xlsx_name=xlsx_name,
        sheet=sheet,
        item_rows=item_rows,
        judge_items=judge_items,
        skipped_standard_items=skipped_standard_items,
        record_only_count=record_only_count,
        resolved_conflicts=resolved_conflicts,
        unrecognized_items=unrecognized,
        standard_sources=standard_sources,
    )


async def write_prepared(
    db: AsyncSession,
    prepared: PreparedImport,
    *,
    user_id: uuid.UUID | None = None,
    user_name: str | None = None,
    on_progress: ProgressCallback | None = None,
) -> QcImportCommitResponse:
    """建品种、写项目、逐批判定、分块写入；每个阶段上报真实进度。

    调用方负责 commit / rollback。
    """

    async def emit(percent: int, message: str, stage: str = "writing") -> None:
        if on_progress is not None:
            await on_progress({"stage": stage, "percent": percent, "message": message})

    product = QcProduct(
        id=prepared.product_id,
        name=prepared.product_name,
        abbr=prepared.abbr,
        category=prepared.category,
        quality_standard=prepared.quality_standard,
        source_file_name=prepared.xlsx_name,
        status="active",
        last_inspected_at=datetime.now(UTC),
        created_by=user_id,
        updated_by=user_id,
    )
    db.add(product)
    await db.flush()

    for row in prepared.item_rows:
        row["created_by"] = user_id
        row["updated_by"] = user_id
    await emit(8, f"正在写入 {len(prepared.item_rows)} 个检验项目")
    await db.execute(insert(QcItem), prepared.item_rows)

    # ── 批次与实测值 ──
    limits_cache: dict[uuid.UUID, ItemLimits] = {
        context.item_id: compile_item_limits(context.judge) for context in prepared.judge_items
    }

    batch_rows: list[dict[str, object]] = []
    value_rows: list[dict[str, object]] = []
    total_batches = len(prepared.sheet.rows)
    for index, sheet_row in enumerate(prepared.sheet.rows, start=1):
        batch_id = uuid.uuid4()
        levels: list[str] = []
        for context in prepared.judge_items:
            actual = sheet_row.values.get(context.column_index)
            result = judge_value(context.judge, actual, limits_cache[context.item_id])
            levels.append(result.level)
            value_rows.append(
                {
                    "id": uuid.uuid4(),
                    "batch_id": batch_id,
                    "item_id": context.item_id,
                    "actual_value": (actual[:255] if actual else None),
                    "numeric_value": result.numeric_value,
                    "level": result.level,
                    "created_by": user_id,
                    "updated_by": user_id,
                }
            )
        batch_rows.append(
            {
                "id": batch_id,
                "product_id": product.id,
                "batch_no": sheet_row.batch_no[:64],
                "level": aggregate_level(levels),
                "source": SOURCE_IMPORT,
                "entered_by_name": user_name,
                "created_by": user_id,
                "updated_by": user_id,
            }
        )
        if index % 200 == 0:
            percent = 12 + int(38 * index / max(total_batches, 1))
            await emit(min(percent, 50), f"正在判定 {index} / {total_batches} 批", stage="parsing")

    await emit(60, "正在写入批次")
    for chunk in _chunks(batch_rows, _BATCH_CHUNK):
        await db.execute(insert(QcBatch), chunk)

    total_values = len(value_rows)
    written = 0
    for chunk in _chunks(value_rows, _VALUE_CHUNK):
        await db.execute(insert(QcValue), chunk)
        written += len(chunk)
        percent = 62 + int(33 * written / max(total_values, 1))
        await emit(min(percent, 95), f"已写入 {written} / {total_values} 条检验值")

    logger.info(
        "qc_report import committed",
        extra={
            "product_id": str(product.id),
            "item_count": len(prepared.item_rows),
            "batch_count": len(batch_rows),
            "value_count": len(value_rows),
            "record_only_count": prepared.record_only_count,
            "skipped_standard_items": len(prepared.skipped_standard_items),
        },
    )
    return QcImportCommitResponse(
        product_id=product.id,
        product_name=product.name,
        item_count=len(prepared.item_rows),
        record_only_count=prepared.record_only_count,
        batch_count=len(batch_rows),
        value_count=len(value_rows),
        unrecognized_items=prepared.unrecognized_items,
        skipped_standard_items=prepared.skipped_standard_items,
        resolved_conflicts=prepared.resolved_conflicts,
        standard_sources=prepared.standard_sources,
    )


async def commit_import(
    db: AsyncSession,
    *,
    docx_bytes: bytes,
    docx_name: str,
    xlsx_bytes: bytes,
    xlsx_name: str,
    name: str,
    abbr: str,
    category: str,
    quality_standard: str | None,
    manual_mapping: dict[str, str] | None = None,
    saved_mapping: dict[str, str] | None = None,
    resolutions: dict[str, str] | None = None,
    user_id: uuid.UUID | None = None,
    user_name: str | None = None,
) -> QcImportCommitResponse:
    """兼容旧调用：解析 + 写入，不订阅进度。调用方负责 commit / rollback。"""
    prepared = prepare_import(
        docx_bytes=docx_bytes,
        docx_name=docx_name,
        xlsx_bytes=xlsx_bytes,
        xlsx_name=xlsx_name,
        name=name,
        abbr=abbr,
        category=category,
        quality_standard=quality_standard,
        manual_mapping=manual_mapping,
        saved_mapping=saved_mapping,
        resolutions=resolutions,
    )
    return await write_prepared(db, prepared, user_id=user_id, user_name=user_name)


class _ItemContext:
    """判定时用的项目上下文。"""

    __slots__ = ("item_id", "column_index", "judge")

    def __init__(self, item_id: uuid.UUID, column_index: int, judge: JudgeItem) -> None:
        self.item_id = item_id
        self.column_index = column_index
        self.judge = judge


__all__ = [
    "commit_import",
    "preview_import",
    "suggest_from_filename",
]
