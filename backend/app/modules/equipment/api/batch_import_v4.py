"""Equipment Import v4 API Routes."""

import logging
import time
from datetime import date, datetime, timedelta
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import ApiResponse, build_response
from app.modules.equipment import repository as repo
from app.modules.equipment.config.dept_mapping import normalize_department_name
from app.modules.equipment.models.equipment import Equipment
from app.modules.equipment.models.import_audit import ImportAuditLog
from app.modules.equipment.schemas.import_v4 import (
    ImportErrorItem,
    ImportV4BatchApiResponse,
    ImportV4BatchResponse,
    ImportV4PreviewApiResponse,
    ImportV4PreviewResponse,
)
from app.modules.equipment.service.import_engine import (
    MatchStrategy,
    apply_incremental_update,
    detect_internal_duplicates,
    find_existing_equipment,
)

router = APIRouter()

PREVIEW_HEADERS = [
    {"key": "row_index", "title": "行号", "width": 60},
    {"key": "asset_no", "title": "资产编号"},
    {"key": "label_no", "title": "标签号"},
    {"key": "name", "title": "设备名称"},
    {"key": "category_description", "title": "资产类别说明"},
    {"key": "equipment_class", "title": "设备分类"},
    {"key": "manufacturer", "title": "制造商"},
    {"key": "model", "title": "型号"},
    {"key": "current_cost", "title": "当前成本"},
    {"key": "book_value", "title": "帐面净值"},
    {"key": "quantity", "title": "数量"},
    {"key": "department_name", "title": "部门"},
    {"key": "location_text", "title": "位置"},
    {"key": "status", "title": "状态"},
    {"key": "scrap_status", "title": "报废状态"},
    {"key": "scrap_time", "title": "报废时间"},
    {"key": "equipment_tag", "title": "设备位号"},
    {"key": "responsible_person_name", "title": "负责人"},
    {"key": "specification", "title": "设备规格"},
    {"key": "supplier", "title": "供应商"},
    {"key": "production_date", "title": "出厂日期"},
    {"key": "commissioning_date", "title": "启用日期"},
    {"key": "description", "title": "描述"},
]

logger = logging.getLogger(__name__)

# 这些字段在数据库中均为字符串列，但 Excel 常以数字单元格存储，需归一化
_TEXT_NORMALIZED_KEYS = (
    "asset_no",
    "label_no",
    "equipment_tag",
    "model",
    "location_text",  # Excel 中可能为数字，需转为字符串
)

# 数据库中为 DATE 列的字段。asyncpg 对其要求 datetime.date 实例，
# 传字符串会报 `'str' object has no attribute 'toordinal'`。
_DATE_KEYS = ("production_date", "commissioning_date", "scrap_time")

# 数据库中为 INTEGER 列的字段。Excel 里常以浮点单元格存储（1.0），
# 直接入库会走 PG 的 assignment cast（2.5 -> 3 四舍五入），语义不可控，故显式取整。
_INT_KEYS = ("quantity",)

# Excel 日期序列号基准（1900 日期系统，含 Excel 的 1900 闰年 bug 修正）
_EXCEL_EPOCH = date(1899, 12, 30)

_DATE_PATTERNS = ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d", "%Y-%m-%d %H:%M:%S")


def _excel_scalar_to_text(value: Any) -> str | None:
    """把 Excel 单元格标量安全转成字符串；59070.0 -> '59070' 而非 '59070.0'。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).strip()
    return text or None


def _coerce_int_value(value: Any) -> int | None:
    """把各���输入归一化为 int；无法识别返回 None（INTEGER 列可空）。"""
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int | float):
        try:
            return int(value)
        except (ValueError, OverflowError):
            return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))  # 兼容 '1.0' 这类文本
    except ValueError:
        logger.warning("无法识别的整数值，已置空: %r", value)
        return None


def _coerce_date_value(value: Any) -> date | None:
    """把各类日期输入归一化为 datetime.date。

    覆盖四种来源：
      - datetime.date / datetime.datetime  -> 直接取 date 部分
      - Excel 日期序列号（46196）          -> 按 1899-12-30 基准换算
      - '2026-04-27' / '2026/4/27' 等文本  -> 按 _DATE_PATTERNS 解析
      - 空串 / None / 无法识别             -> None（DATE 列可空）
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, int | float) and not isinstance(value, bool):
        # Excel 日期序列号，如 46196 -> 2026-06-24
        try:
            return _EXCEL_EPOCH + timedelta(days=int(value))
        except (ValueError, OverflowError):
            return None
    text = str(value).strip()
    if not text:
        return None
    for pattern in _DATE_PATTERNS:
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    logger.warning("无法识别的日期值，已置空: %r", value)
    return None


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    """Apply FIELD_MAP key mapping and type coercion to a single Excel row."""
    new_row = {FIELD_MAP.get(str(k).strip(), str(k).strip()): v for k, v in row.items()}
    for key in _TEXT_NORMALIZED_KEYS:
        if new_row.get(key) is None:
            continue
        new_row[key] = _excel_scalar_to_text(new_row[key])
    for key in _DATE_KEYS:
        if new_row.get(key) is None:
            continue
        new_row[key] = _coerce_date_value(new_row[key])
    for key in _INT_KEYS:
        if new_row.get(key) is None:
            continue
        new_row[key] = _coerce_int_value(new_row[key])
    return new_row


# Excel 中文表头 -> 数据库字段。
# 必须与 /preview、/batch 共用同一份，否则两处行为会静默漂移。
FIELD_MAP: dict[str, str] = {
    "资产编号": "asset_no",
    "标签号": "label_no",
    "设备名称": "name",
    "资产类别说明": "category_description",
    "数量": "quantity",
    "制造商": "manufacturer",
    "型号": "model",
    "当前成本": "current_cost",
    "帐面净值": "book_value",
    "启用日期": "commissioning_date",
    "实物所在部门": "department_name",
    "实物所在地点": "location_text",
    "报废状态": "scrap_status",
    "报废时间": "scrap_time",
    "设备位号": "equipment_tag",
    "设备分类": "equipment_class",
    "负责人": "responsible_person_name",
    "设备状态": "status",
    "设备规格": "specification",
    "供应商": "supplier",
    "出厂日期": "production_date",
    "描述": "description",
}

# Equipment 模型实际存在的列。FIELD_MAP 里有两类键不属于模型：
#   - department_name：解析用中间变量，最终写入的是 department_id
#   - quantity：Excel 有该列，但数据库未设计此字段
# 直接 `Equipment(**row)` 会因多余关键字抛 TypeError，故入库前必须按白名单过滤。
_EQUIPMENT_COLUMNS = frozenset(Equipment.__table__.columns.keys())

# 被过滤掉的字段及其原因，供日志提示
_DROPPED_FIELDS = tuple(sorted(set(FIELD_MAP.values()) - _EQUIPMENT_COLUMNS))


def _only_model_fields(row: dict[str, Any]) -> dict[str, Any]:
    """只保留 Equipment 模型真实存在的列，避免 `Equipment(**row)` 抛 TypeError。"""
    return {k: v for k, v in row.items() if k in _EQUIPMENT_COLUMNS}

async def resolve_department_strict(excel_dept: str, db: AsyncSession) -> tuple[str | None, Any, str | None]:
    if not excel_dept or not str(excel_dept).strip():
        return None, None, "部门名称为空"
    standard_name = normalize_department_name(str(excel_dept).strip())
    if not standard_name:
        return None, None, f"部门'{excel_dept}'未在映射表中定义"

    from app.modules.hr.public_api import get_department_by_name

    if not (dept := await get_department_by_name(db, standard_name)):
        return None, None, f"标准化部门'{standard_name}'在数据库中不存在"
    return standard_name, dept.id, None


async def log_audit(db: AsyncSession, batch_id: str, operation_type: str, **kwargs: Any) -> None:
    db.add(ImportAuditLog(batch_id=batch_id, operation_type=operation_type, **kwargs))


@router.post("/batch", summary="执行批量导入 (v4)", response_model=ImportV4BatchApiResponse)
async def batch_import_v4(
    current_user: RequiredUser,
    request: Annotated[dict[str, Any], Body(...)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    data = request.get("data", [])
    force_override = request.get("force_override_business_fields", False)

    if _DROPPED_FIELDS:
        logger.warning(
            "Excel 中以下字段在 Equipment 模型不存在，导入时会被丢弃: %s",
            ", ".join(_DROPPED_FIELDS),
        )

    normalized_data = [_normalize_row(row) for row in data]

    duplicates = detect_internal_duplicates(normalized_data)
    batch_id = f"import_{int(time.time())}_{current_user.id.hex[:8]}"
    created = updated = skipped = failed = 0
    errors: list[dict[str, Any]] = []
    unmapped_depts: dict[str, list[int]] = {}

    for idx, row in enumerate(normalized_data):
        audit_kwargs = {
            "row_index": idx,
            "asset_no": row.get("asset_no"),
            "equipment_tag": row.get("equipment_tag"),
            "department_id": row.get("department_id"),
            "location_text": row.get("location_text"),
        }

        # try 必须包在 begin_nested 外层
        try:
            async with db.begin_nested():
                if idx in duplicates:
                    skipped += 1
                    await log_audit(db, batch_id, "skip", match_strategy="internal_duplicate", **audit_kwargs)
                    continue

                dept_raw = row.get("department_name")
                dept_name, dept_id, dept_error = await resolve_department_strict(dept_raw, db)  # type: ignore[arg-type]

                if dept_error:
                    failed += 1
                    errors.append({"row": idx, "error": dept_error})
                    if dept_raw:
                        unmapped_depts.setdefault(dept_raw, []).append(idx)
                    await log_audit(db, batch_id, "error", error_message=dept_error, **audit_kwargs)
                    continue

                row["department_id"] = dept_id
                existing, strategy, warnings = await find_existing_equipment(
                    db,
                    row.get("asset_no"),
                    row.get("equipment_tag"),
                    row.get("name"),
                    dept_id,
                    row.get("location_text"),
                    force_override,
                )

                if strategy == MatchStrategy.TAG_CONFLICT:
                    failed += 1
                    err_msg = "设备位号冲突，无法创建"
                    errors.append({"row": idx, "error": err_msg})
                    await log_audit(
                        db, batch_id, "error", match_strategy=strategy, error_message=err_msg, **audit_kwargs
                    )
                    continue

                if existing:
                    changes = apply_incremental_update(existing, row, force_override)
                    override_type = "force" if (force_override and changes) else "normal"
                    if changes:
                        updated += 1
                        await log_audit(
                            db,
                            batch_id,
                            "update",
                            match_strategy=strategy,
                            changes=changes,
                            override_type=override_type,
                            warnings=warnings,
                            **audit_kwargs,
                        )
                    else:
                        skipped += 1
                        await log_audit(db, batch_id, "skip", match_strategy=strategy, **audit_kwargs)
                else:
                    await repo.create_equipment(db, _only_model_fields(row))
                    created += 1
                    await log_audit(db, batch_id, "create", match_strategy=strategy, **audit_kwargs)
        except Exception:
            failed += 1
            errors.append({"row": idx, "error": "导入处理异常，请检查数据格式"})
            logger.exception("v4 import row %s failed", idx)
            await log_audit(db, batch_id, "error", error_message="导入处理异常", **audit_kwargs)

    return build_response(
        data=ImportV4BatchResponse(
            batch_id=batch_id,
            created_count=created,
            updated_count=updated,
            skipped_count=skipped,
            error_count=failed,
            unmapped_departments=unmapped_depts,
            errors=[ImportErrorItem(row=e["row"], error=e["error"]) for e in errors],
        )
    )


        return build_response(data=ImportV4PreviewResponse(items=[], total=0, headers=PREVIEW_HEADERS))
@router.post("/preview", summary="预览导入结果 (v4)", response_model=ImportV4PreviewApiResponse)
async def preview_import_v4(
    current_user: RequiredUser,
    data: Annotated[list[dict[str, Any]], Body(...)],
    force_override: bool = Body(False),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    results = []
    # 对所有行进行完整字段映射，确保业务字段全部存在
    normalized_data = [_normalize_row(row) for row in data]

    # 使用映射后的数据进行去重检测
    duplicates = detect_internal_duplicates(normalized_data)

    for idx, row in enumerate(normalized_data):
        # 1. 使用映射后的行数据，确保包含所有 22 个英文键名
        display_row = dict(row)

        # 2. 后台静默解析部门，用于校验和匹配逻辑
        dept_raw = row.get("department_name")
        dept_name, dept_id, dept_error = await resolve_department_strict(dept_raw, db)  # type: ignore[arg-type]

        # 3. 调用匹配引擎预览匹配策略（P2: 使用 forceOverride 参数）
        match_strategy = None
        if not dept_error and idx not in duplicates and dept_id:
            row["department_id"] = dept_id
            existing, strategy, warnings = await find_existing_equipment(
                db,
                row.get("asset_no"),
                row.get("equipment_tag"),
                row.get("name"),
                dept_id,
                row.get("location_text"),
                force_override,
            )
            match_strategy = strategy
            if warnings:
                display_row["match_warnings"] = [w["message"] for w in warnings]

        # 4. 组装返回结果
        result_item = {
            "row_index": idx,
            "is_duplicate": idx in duplicates,
            "validation_status": "error" if dept_error else ("duplicate" if idx in duplicates else "pass"),
            "error_message": dept_error,
            "resolved_department": dept_name,
            "match_strategy": match_strategy,
        }
        # 将原始 Excel 数据合并进去，确保前端看到的列名和值与 Excel 完全一致
        result_item.update(display_row)

        # 部门列改为展示标准化后的名称（如"检验室" -> "质量控制部"），
        # 让用户确认映射是否符合预期；解析失败时保留原值以便对照排查。
        if dept_name:
            result_item["department_name"] = dept_name

        results.append(result_item)

    if results:
        return build_response(data=ImportV4PreviewResponse(items=results, total=len(results), headers=PREVIEW_HEADERS))
