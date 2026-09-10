"""Equipment Import v4 API Routes."""
import time, uuid, logging
from typing import Any, Annotated
from fastapi import APIRouter, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import ApiResponse, build_response
from app.modules.equipment.models.import_audit import ImportAuditLog
from app.modules.equipment.service.import_engine import (
    preprocess_excel_row,
    apply_incremental_update, detect_internal_duplicates, find_existing_equipment
)
from app.modules.equipment import repository as repo
from app.modules.equipment.config.dept_mapping import normalize_department_name

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

async def resolve_department_strict(excel_dept: str, db: AsyncSession):
    if not excel_dept or not str(excel_dept).strip(): return None, None, "部门名称为空"
    standard_name = normalize_department_name(str(excel_dept).strip())
    if not standard_name: return None, None, f"部门'{excel_dept}'未在映射表中定义"
    
    from app.modules.hr.public_api import get_department_by_name
    if not (dept := await get_department_by_name(db, standard_name)):
        return None, None, f"标准化部门'{standard_name}'在数据库中不存在"
    return standard_name, dept.id, None

async def log_audit(db, batch_id, operation_type, **kwargs):
    db.add(ImportAuditLog(batch_id=batch_id, operation_type=operation_type, **kwargs))

@router.post("/batch", summary="执行批量导入 (v4)")
async def batch_import_v4(
    current_user: RequiredUser,
    request: Annotated[dict[str, Any], Body(...)],
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    data = request.get("data", [])
    force_override = request.get("force_override_business_fields", True)
    
    # 字段映射
    FIELD_MAP = {
        "资产编号": "asset_no", "标签号": "label_no", "设备名称": "name",
        "资产类别说明": "category_description", "数量": "quantity",
        "制造商": "manufacturer", "型号": "model", "当前成本": "current_cost",
        "帐面净值": "book_value", "启用日期": "commissioning_date",
        "实物所在部门": "department_name", "实物所在地点": "location_text",
        "报废状态": "scrap_status", "报废时间": "scrap_time",
        "设备位号": "equipment_tag", "设备分类": "equipment_class",
        "负责人": "responsible_person_name", "设备状态": "status",
        "设备规格": "specification", "供应商": "supplier",
        "出厂日期": "production_date", "描述": "description"
    }
    normalized_data = [{FIELD_MAP.get(k.strip(), k.strip()): v for k, v in row.items()} for row in data]
    
    duplicates = detect_internal_duplicates(normalized_data)
    batch_id = f"import_{int(time.time())}_{current_user.id.hex[:8]}"
    created = updated = skipped = failed = 0
    errors, unmapped_depts = [], {}

    for idx, row in enumerate(normalized_data):
        async with db.begin_nested():
            try:
                if idx in duplicates:
                    skipped += 1; continue
                
                dept_raw = row.get("department_name")
                dept_name, dept_id, dept_error = await resolve_department_strict(dept_raw, db)
                
                if dept_error:
                    failed += 1; errors.append({"row": idx, "error": dept_error})
                    if dept_raw: unmapped_depts.setdefault(dept_raw, []).append(idx)
                    continue
                
                row["department_id"] = dept_id
                existing, strategy, warnings = await find_existing_equipment(
                    db, row.get("asset_no"), row.get("equipment_tag"), row.get("name"), dept_id, row.get("location_text"))
                
                if existing:
                    changes = apply_incremental_update(existing, row, force_override)
                    if changes: updated += 1
                    else: skipped += 1
                else:
                    await repo.create_equipment(db, row); created += 1
            except Exception as e:
                failed += 1; errors.append({"row": idx, "error": str(e)})

    return build_response(data={
        "batch_id": batch_id, "created_count": created, "updated_count": updated,
        "skipped_count": skipped, "error_count": failed, "unmapped_departments": unmapped_depts
    })

@router.post("/preview", summary="预览导入结果 (v4)")
async def preview_import_v4(
    current_user: RequiredUser,
    data: Annotated[list[dict[str, Any]], Body(...)],
    force_override: bool = Body(True),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    results = []
    FIELD_MAP = {
        "资产编号": "asset_no", "标签号": "label_no", "设备名称": "name",
        "资产类别说明": "category_description", "数量": "quantity",
        "制造商": "manufacturer", "型号": "model", "当前成本": "current_cost",
        "帐面净值": "book_value", "启用日期": "commissioning_date",
        "实物所在部门": "department_name", "实物所在地点": "location_text",
        "报废状态": "scrap_status", "报废时间": "scrap_time",
        "设备位号": "equipment_tag", "设备分类": "equipment_class",
        "负责人": "responsible_person_name", "设备状态": "status",
        "设备规格": "specification", "供应商": "supplier",
        "出厂日期": "production_date", "描述": "description"
    }
    # 对所有行进行完整字段映射，确保 22 个字段全部存在
    normalized_data = []
    for row in data:
        new_row = {}
        for k, v in row.items():
            clean_key = str(k).strip()
            mapped_key = FIELD_MAP.get(clean_key, clean_key)
            new_row[mapped_key] = v
        normalized_data.append(new_row)
    
    # 使用映射后的数据进行去重检测
    duplicates = detect_internal_duplicates(normalized_data)

    for idx, row in enumerate(normalized_data):
        # 1. 使用映射后的行数据，确保包含所有 22 个英文键名
        display_row = dict(row) 
        
        # 2. 后台静默解析部门，用于校验和匹配逻辑
        dept_raw = row.get("department_name")
        dept_name, dept_id, dept_error = await resolve_department_strict(dept_raw, db)
        
        # 3. 组装返回结果
        result_item = {
            "row_index": idx,
            "is_duplicate": idx in duplicates,
            "validation_status": "error" if dept_error else ("duplicate" if idx in duplicates else "pass"),
            "error_message": dept_error,
            "resolved_department": dept_name, # 仅用于调试或额外展示
        }
        # 将原始 Excel 数据合并进去，确保前端看到的列名和值与 Excel 完全一致
        result_item.update(display_row)
        
        results.append(result_item)
        
    if results:
        logger.info(f"[DEBUG-PREVIEW] First item keys: {list(results[0].keys())}")
    return build_response(data={
        "items": results, 
        "total": len(results),
        "headers": PREVIEW_HEADERS
    })
