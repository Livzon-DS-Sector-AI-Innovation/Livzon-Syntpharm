"""Equipment Import v4 Core Logic Engine."""

import logging
import uuid
from enum import StrEnum
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.equipment.models.equipment import Equipment
from app.modules.equipment.schemas.import_v4 import ChangeRecord, WarningInfo

logger = logging.getLogger(__name__)


class MatchStrategy(StrEnum):
    COMPOSITE = "composite"
    ASSET_NO_ONLY = "asset_no_only"
    TAG = "tag"
    TAG_CONFLICT = "tag_conflict"
    FUZZY = "fuzzy"
    NONE = "none"


MONEY_FIELDS = ["current_cost", "book_value"]
OVERRIDEABLE_BUSINESS_FIELDS = [
    "label_no",
    "equipment_tag",
    "equipment_class",
    "name",
    "responsible_person_name",
    "status",
    "category_description",
    "model",
    "specification",
    "manufacturer",
    "supplier",
    "scrap_status",
    "scrap_time",
    "production_date",
    "commissioning_date",
    "description",
    "department_id",
    "location_text",
]


async def find_existing_equipment(
    db: AsyncSession,
    asset_no: str | None,
    equipment_tag: str | None,
    name: str | None,
    department_id: uuid.UUID | None,
    location_text: str | None,
    force_override: bool = False,
) -> tuple[Equipment | None, MatchStrategy, list[dict[str, str]]]:
    warnings: list[dict[str, str]] = []
    # P1: 复合主键精确匹配
    if asset_no and department_id and location_text:
        result = await db.execute(
            select(Equipment).where(
                Equipment.asset_no == asset_no,
                Equipment.department_id == department_id,
                Equipment.location_text == location_text,
                Equipment.is_deleted.is_(False),
            )
        )
        if eq := result.scalar_one_or_none():
            return eq, MatchStrategy.COMPOSITE, warnings

    # P1.5: 强制覆盖模式下，仅按资产编号匹配（部门/位置可能不一致）
    if force_override and asset_no:
        # 标准化资产编号：去除首尾空格和前导零，确保 "059070" 和 "59070" 能匹配
        normalized_asset_no = str(asset_no).strip().lstrip("0") or "0"
        logger.info("Force override: searching for asset_no=%s (normalized=%s)", asset_no, normalized_asset_no)

        # 先尝试精确匹配
        result = await db.execute(
            select(Equipment).where(Equipment.asset_no == asset_no, Equipment.is_deleted.is_(False))
        )
        eq = result.scalar_one_or_none()

        # 如果精确匹配失败，尝试标准化后匹配
        if not eq:
            from sqlalchemy import func

            result = await db.execute(
                select(Equipment).where(
                    Equipment.is_deleted.is_(False), func.ltrim(Equipment.asset_no, "0") == normalized_asset_no
                )
            )
            eq = result.scalar_one_or_none()
            if eq:
                logger.info("Matched by normalized asset_no: DB=%s vs Excel=%s", eq.asset_no, asset_no)

        if eq:
            warnings.append(
                {
                    "field": "asset_no",
                    "level": "WARN",
                    "message": f"资产编号匹配但部门/位置不一致，强制覆盖将更新 (DB: {eq.asset_no})",
                }
            )
            return eq, MatchStrategy.ASSET_NO_ONLY, warnings

    # P2: 设备位号匹配
    if equipment_tag:
        result = await db.execute(
            select(Equipment).where(Equipment.equipment_tag == equipment_tag, Equipment.is_deleted.is_(False))
        )
        if eq := result.scalar_one_or_none():
            if asset_no and eq.asset_no != asset_no:
                return (
                    None,
                    MatchStrategy.TAG_CONFLICT,
                    [{"field": "equipment_tag", "level": "ERROR", "message": "Tag conflict"}],
                )
            return eq, MatchStrategy.TAG, warnings

    # P3: 模糊匹配
    if not asset_no and not equipment_tag and name and department_id and location_text:
        result = await db.execute(
            select(Equipment).where(
                Equipment.name == name,
                Equipment.department_id == department_id,
                Equipment.location_text == location_text,
                Equipment.is_deleted.is_(False),
            )
        )
        if eq := result.scalar_one_or_none():
            return eq, MatchStrategy.FUZZY, warnings

    return None, MatchStrategy.NONE, warnings


def detect_internal_duplicates(rows: list[dict[str, Any]]) -> set[int]:
    seen, duplicates = {}, set()
    for idx, row in enumerate(rows):
        key = (row.get("asset_no"), row.get("department_id") or row.get("department_name"), row.get("location_text"))
        if all(key):
            if key in seen:
                duplicates.add(idx)
            else:
                seen[key] = idx
    return duplicates


def apply_incremental_update(
    existing: Equipment, excel_data: dict[str, Any], force_override: bool = False
) -> dict[str, ChangeRecord]:
    changes: dict[str, ChangeRecord] = {}
    for field in MONEY_FIELDS:
        new_val = excel_data.get(field)
        if isinstance(new_val, str) and not new_val.strip():
            new_val = None
        if getattr(existing, field) != new_val:
            changes[field] = {"old": getattr(existing, field), "new": new_val}  # type: ignore[assignment]
            setattr(existing, field, new_val)

    for field in OVERRIDEABLE_BUSINESS_FIELDS:
        new_val = excel_data.get(field)
        if new_val is None:
            continue
        if force_override or getattr(existing, field) is None:
            if getattr(existing, field) != new_val:
                changes[field] = {"old": getattr(existing, field), "new": new_val}  # type: ignore[assignment]
                setattr(existing, field, new_val)
    return changes


def preprocess_excel_row(row: dict[str, Any]) -> dict[str, Any]:
    """将 Excel 中的空字符串转换为 None，并处理日期格式。"""
    processed: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, str) and not v.strip():
            processed[k] = None
        else:
            processed[k] = v
    return processed
