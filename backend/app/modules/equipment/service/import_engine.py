"""Equipment Import v4 Core Logic Engine."""
import uuid, logging
from typing import Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.equipment.models.equipment import Equipment
from app.modules.equipment.schemas.import_v4 import WarningInfo, ChangeRecord

logger = logging.getLogger(__name__)
A_FIELDS = ["current_cost", "book_value"]
B_FIELDS = ["label_no", "equipment_tag", "equipment_class", "name", "responsible_person_name", 
            "status", "category_description", "model", "specification", "manufacturer", 
            "supplier", "scrap_status", "scrap_time", "production_date", "commissioning_date", 
            "description", "department_id", "location_text"]

async def find_existing_equipment(db: AsyncSession, asset_no: str | None, equipment_tag: str | None, 
                                  name: str | None, department_id: uuid.UUID | None, location_text: str | None):
    warnings: list[WarningInfo] = []
    # P1: 复合主键精确匹配
    if asset_no and department_id and location_text:
        result = await db.execute(select(Equipment).where(
            Equipment.asset_no == asset_no, Equipment.department_id == department_id,
            Equipment.location_text == location_text, Equipment.is_deleted.is_(False)))
        if (eq := result.scalar_one_or_none()): return eq, "composite", warnings
    
    # P2: 设备位号匹配
    if equipment_tag:
        result = await db.execute(select(Equipment).where(
            Equipment.equipment_tag == equipment_tag, Equipment.is_deleted.is_(False)))
        if (eq := result.scalar_one_or_none()):
            if asset_no and eq.asset_no != asset_no:
                return None, "tag_conflict", [{"field": "equipment_tag", "level": "ERROR", "message": "Tag conflict"}]
            return eq, "tag", warnings
            
    # P3: 模糊匹配
    if not asset_no and not equipment_tag and name and department_id and location_text:
        result = await db.execute(select(Equipment).where(
            Equipment.name == name, Equipment.department_id == department_id,
            Equipment.location_text == location_text, Equipment.is_deleted.is_(False)))
        if (eq := result.scalar_one_or_none()): return eq, "fuzzy", warnings
        
    return None, "none", warnings

def detect_internal_duplicates(rows: list[dict[str, Any]]) -> set[int]:
    seen, duplicates = {}, set()
    for idx, row in enumerate(rows):
        key = (row.get("asset_no"), row.get("department_id") or row.get("department_name"), row.get("location_text"))
        if all(key):
            if key in seen: duplicates.add(idx)
            else: seen[key] = idx
    return duplicates

def apply_incremental_update(existing: Equipment, excel_data: dict[str, Any], force_override: bool = False):
    changes: dict[str, ChangeRecord] = {}
    for field in A_FIELDS:
        new_val = excel_data.get(field)
        if isinstance(new_val, str) and not new_val.strip(): new_val = None
        if getattr(existing, field) != new_val:
            changes[field] = {"old": getattr(existing, field), "new": new_val}
            setattr(existing, field, new_val)
            
    for field in B_FIELDS:
        new_val = excel_data.get(field)
        if new_val is None: continue
        if force_override or getattr(existing, field) is None:
            if getattr(existing, field) != new_val:
                changes[field] = {"old": getattr(existing, field), "new": new_val}
                setattr(existing, field, new_val)
    return changes


def preprocess_excel_row(row: dict[str, Any]) -> dict[str, Any]:
    """将 Excel 中的空字符串转换为 None，并处理日期格式。"""
    processed = {}
    for k, v in row.items():
        if isinstance(v, str) and not v.strip():
            processed[k] = None
        else:
            processed[k] = v
    return processed
