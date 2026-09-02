"""Equipment service layer: business logic, validation, transaction orchestration."""

import datetime
import uuid
from io import BytesIO
from typing import Any, TypedDict

import pandas as pd
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException, DuplicateException, NotFoundException
from app.modules.equipment import repository as repo
from app.modules.equipment.models import Equipment, EquipmentCategory, Location
from app.modules.equipment.models.equipment import EquipmentSyncLog
from app.modules.equipment.schemas import (
    EquipmentCategoryCreate,
    EquipmentCategoryUpdate,
    EquipmentCreate,
    EquipmentSyncResult,
    EquipmentUpdate,
    LocationCreate,
    LocationUpdate,
)
from app.modules.hr.models import HrDepartment

from .validation import (
    validate_asset_no_unique,
    validate_categories_exist,
    validate_category_exists,
    validate_equipment_exists,
    validate_location_exists,
    validate_unique_category_code,
    validate_unique_location_code,
)


# ==================== 设备分类 ====================
async def create_equipment_category(
    db: AsyncSession,
    data: EquipmentCategoryCreate,
) -> EquipmentCategory:
    """创建设备分类"""
    await validate_unique_category_code(db, data.code)
    return await repo.create_equipment_category(db, data.model_dump())


# ==================== 同步配置常量 ====================
EXCEL_HEADER_ROW = 4  # Excel 数据起始行（从 0 开始计数，header=4 表示第 5 行）
MISSING_ASSET_THRESHOLD = 0.05  # 缺失设备比例阈值（5%），超过则触发熔断
MAX_CHANGES_LOG_ENTRIES = 1000  # 审计日志最大记录数


async def get_equipment_category_by_id(
    db: AsyncSession,
    category_id: uuid.UUID,
) -> EquipmentCategory:
    """获取设备分类"""
    category = await repo.get_equipment_category_by_id(db, category_id)
    if not category:
        raise NotFoundException("设备分类", str(category_id))
    return category


async def get_equipment_categories(
    db: AsyncSession,
    parent_id: uuid.UUID | None = None,
) -> list[EquipmentCategory]:
    """获取设备分类列表"""
    return await repo.get_equipment_categories(db, parent_id)


async def get_equipment_category_tree(db: AsyncSession) -> list[EquipmentCategory]:
    """获取设备分类树形结构"""
    return await repo.get_equipment_category_tree(db)


async def update_equipment_category(
    db: AsyncSession,
    category_id: uuid.UUID,
    data: EquipmentCategoryUpdate,
) -> EquipmentCategory:
    """更新设备分类"""
    if data.code is not None:
        await validate_unique_category_code(db, data.code, exclude_id=category_id)

    category = await repo.update_equipment_category(db, category_id, data.model_dump(exclude_unset=True))
    if not category:
        raise NotFoundException("设备分类", str(category_id))
    return category


async def delete_equipment_category(
    db: AsyncSession,
    category_id: uuid.UUID,
) -> bool:
    """删除设备分类"""
    await validate_category_exists(db, category_id)

    children = await repo.get_equipment_categories(db, parent_id=category_id)
    if children:
        raise AppException(message="该分类下存在子分类，无法删除")

    equipment_count = await repo.count_equipments_by_category(db, category_id)
    if equipment_count > 0:
        raise AppException(message="该分类下存在关联设备，无法删除")

    return await repo.delete_equipment_category(db, category_id)


# ==================== 位置管理 ====================
async def create_location(
    db: AsyncSession,
    data: LocationCreate,
) -> Location:
    """创建位置"""
    await validate_unique_location_code(db, data.code)
    return await repo.create_location(db, data.model_dump())


async def get_location_by_id(
    db: AsyncSession,
    location_id: uuid.UUID,
) -> Location:
    """获取位置"""
    location = await repo.get_location_by_id(db, location_id)
    if not location:
        raise NotFoundException("位置", str(location_id))
    return location


async def get_locations(
    db: AsyncSession,
    parent_id: uuid.UUID | None = None,
) -> list[Location]:
    """获取位置列表"""
    return await repo.get_locations(db, parent_id)


async def get_location_tree(db: AsyncSession) -> list[Location]:
    """获取位置树形结构"""
    return await repo.get_location_tree(db)


async def update_location(
    db: AsyncSession,
    location_id: uuid.UUID,
    data: LocationUpdate,
) -> Location:
    """更新位置"""
    if data.code is not None:
        await validate_unique_location_code(db, data.code, exclude_id=location_id)

    location = await repo.update_location(db, location_id, data.model_dump(exclude_unset=True))
    if not location:
        raise NotFoundException("位置", str(location_id))
    return location


async def delete_location(
    db: AsyncSession,
    location_id: uuid.UUID,
) -> bool:
    """删除位置"""
    await validate_location_exists(db, location_id)

    children = await repo.get_locations(db, parent_id=location_id)
    if children:
        raise AppException(message="该位置下存在子位置，无法删除")

    equipment_count = await repo.count_equipments_by_location(db, location_id)
    if equipment_count > 0:
        raise AppException(message="该位置下存在关联设备，无法删除")

    return await repo.delete_location(db, location_id)


# ==================== 设备管理 ====================
async def generate_equipment_no(
    db: AsyncSession,
    category_code: str,
) -> str:
    """生成设备编号"""
    max_no = await repo.get_max_equipment_no_by_category(db, category_code)
    if max_no:
        # 提取序号部分
        seq_str = max_no.split("-")[-1]
        seq = int(seq_str) + 1
    else:
        seq = 1
    return f"EQ-{category_code}-{seq:04d}"


async def create_equipment(
    db: AsyncSession,
    data: EquipmentCreate,
) -> Equipment:
    """创建设备"""
    # 校验资产编号唯一性
    await validate_asset_no_unique(db, data.asset_no)

    # 验证分类（如果提供了）
    if data.category_ids:
        await validate_categories_exist(db, data.category_ids)

    # 验证位置（如果提供了）
    if data.location_id:
        await validate_location_exists(db, data.location_id)

    equipment_data = data.model_dump()

    try:
        return await repo.create_equipment(db, equipment_data)
    except IntegrityError:
        raise DuplicateException("资产编号", data.asset_no)


async def get_equipment_by_id(
    db: AsyncSession,
    equipment_id: uuid.UUID,
) -> Equipment:
    """获取设备"""
    equipment = await repo.get_equipment_by_id(db, equipment_id)
    if not equipment:
        raise NotFoundException("设备", str(equipment_id))
    return equipment


async def get_equipments(
    db: AsyncSession,
    category_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    status: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Equipment], int]:
    """获取设备列表"""
    return await repo.get_equipments(db, category_id, location_id, department_id, status, keyword, page, page_size)


async def update_equipment(
    db: AsyncSession,
    equipment_id: uuid.UUID,
    data: EquipmentUpdate,
) -> Equipment:
    """更新设备"""
    await validate_equipment_exists(db, equipment_id)

    if data.category_ids:
        await validate_categories_exist(db, data.category_ids)

    if data.location_id is not None:
        await validate_location_exists(db, data.location_id)

    update_data = data.model_dump(exclude_unset=True)

    # 如果只传了负责人姓名没传ID，将ID置空保持一致性
    if "responsible_person_name" in update_data and "responsible_person_id" not in update_data:
        update_data["responsible_person_id"] = None

    return await repo.update_equipment(db, equipment_id, update_data)  # type: ignore[return-value]


async def delete_equipment(
    db: AsyncSession,
    equipment_id: uuid.UUID,
) -> bool:
    """删除设备"""
    equipment = await get_equipment_by_id(db, equipment_id)
    equipment.is_deleted = True
    await db.flush()
    return True


async def get_equipment_statistics(
    db: AsyncSession,
    category_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """获取设备统计（支持筛选）"""
    return await repo.get_equipment_statistics(db, category_id, location_id, department_id, status)


async def get_departments_for_select(db: AsyncSession) -> list[dict[str, Any]]:
    """获取可选部门列表（含负责人），供下拉使用"""
    return await repo.get_departments_for_select(db)


async def batch_delete_equipments(db: AsyncSession, ids: list[uuid.UUID]) -> int:
    """批量删除设备（软删除）"""
    deleted_count = 0
    for eid in ids:
        equipment = await get_equipment_by_id(db, eid)
        if equipment and not equipment.is_deleted:
            equipment.is_deleted = True
            deleted_count += 1
    await db.commit()
    return deleted_count


# 部门名称映射表（标准化处理）
DEPT_MAPPING = {
    # 示例：可以根据实际情况扩展
}


def _get_standard_dept(raw_dept: str | None, valid_depts: set) -> str | None:
    """标准化部门名称"""
    if not raw_dept or pd.isna(raw_dept):
        return None
    raw = str(raw_dept).strip()
    return DEPT_MAPPING.get(raw, raw if raw in valid_depts else None)


# ==================== Excel 智能同步 ====================


async def _prepare_sync_context(db: AsyncSession) -> tuple[dict, dict, dict, list]:
    """准备同步所需的映射表和索引"""
    dept_result = await db.execute(select(HrDepartment.id, HrDepartment.name))
    dept_map = {n: i for i, n in dept_result.fetchall()}
    valid_depts = set(dept_map.keys())

    loc_result = await db.execute(select(Location.id, Location.name))
    loc_map = {n: i for i, n in loc_result.fetchall()}

    # TODO: Refactor to EquipmentRepository.get_all_active()
    equip_result = await db.execute(select(Equipment).where(not Equipment.is_deleted))
    all_active = equip_result.scalars().all()

    combo_index = {(e.asset_no, e.department_id, e.location_id): e for e in all_active}
    asset_index = {}
    for e in all_active:
        asset_index.setdefault(e.asset_no, []).append(e)

    return dept_map, valid_depts, loc_map, all_active, combo_index, asset_index


def _parse_excel_file(file_content: bytes) -> pd.DataFrame:
    """解析 Excel 文件"""
    try:
        return pd.read_excel(BytesIO(file_content), header=EXCEL_HEADER_ROW)
    except Exception as e:
        raise ValueError(f"Excel 解析失败: {str(e)}")


def _build_equipment_update_values(
    row: pd.Series, dept_map: dict, loc_map: dict, valid_depts: set
) -> tuple[dict, list]:
    """构建设备更新值字典和变更日志"""
    asset_no = str(row["资产编号"]).strip()
    if not asset_no:
        return {}, []

    std_dept = _get_standard_dept(row["实物所在部门"], valid_depts)
    dept_id = dept_map.get(std_dept) if std_dept else None

    loc_text = (
        str(row["实物所在地点"]).strip()
        if pd.notna(row["实物所在地点"]) and str(row["实物所在地点"]).strip() != "-"
        else None
    )
    loc_id = loc_map.get(loc_text) if loc_text else None

    new_vals: EquipmentUpdateValues = {}
    changes_log = []

    # 构建更新字段（根据实际业务需求）
    if dept_id:
        new_vals["department_id"] = dept_id
    if loc_id:
        new_vals["location_id"] = loc_id
    if loc_text:
        new_vals["location_text"] = loc_text

    # 添加其他字段的更新逻辑...

    return new_vals, changes_log


async def sync_equipments_with_audit(
    db: AsyncSession,
    file_content: bytes,
    operator_id: uuid.UUID | None = None,
    file_name: str = "unknown.xlsx",
    dry_run: bool = False,
) -> EquipmentSyncResult:
    """TB-04: 带审计追踪、熔断保护及 Dry Run 的最终版同步逻辑"""
    try:
        df = pd.read_excel(BytesIO(file_content), header=EXCEL_HEADER_ROW)
    except Exception as e:
        raise ValueError(f"Excel 解析失败: {str(e)}")

    dept_map, valid_depts, loc_map, all_active, combo_index, asset_index = await _prepare_sync_context(db)

    updated, inserted, migrated, deleted = 0, 0, 0, 0
    processed_ids = set()
    changes_log = []
    warnings = []

    for _, row in df.iterrows():
        asset_no = str(row["资产编号"]).strip()
        if not asset_no:
            continue

        std_dept = _get_standard_dept(row["实物所在部门"], valid_depts)
        dept_id = dept_map.get(std_dept) if std_dept else None
        loc_text = (
            str(row["实物所在地点"]).strip()
            if pd.notna(row["实物所在地点"]) and str(row["实物所在地点"]).strip() != "-"
            else None
        )
        loc_id = loc_map.get(loc_text) if loc_text else None

        # 修复匹配逻辑：优先精确匹配，其次容错匹配
        target_equip = combo_index.get((asset_no, dept_id, loc_id))

        if not target_equip and loc_id is None:
            # 如果位置为空，尝试只匹配资产号和部门
            candidates = [e for e in asset_index.get(asset_no, []) if e.department_id == dept_id]
            if len(candidates) > 1:
                # 发现多条潜在记录，记录警告并跳过，防止误更新
                warnings.append(f"资产 {asset_no} 在部门 {std_dept} 下存在多条位置为空的记录，已跳过同步。")
                continue
            elif len(candidates) == 1:
                target_equip = candidates[0]

        new_vals = {
            "name": str(row["设备名称"]).strip(),
            "current_cost": float(row["当前成本"]) if pd.notna(row["当前成本"]) else None,
            "book_value": float(row["帐面净值"]) if pd.notna(row["帐面净值"]) else None,
            "department_id": dept_id,
            "location_id": loc_id,
            "location_text": loc_text,
            "model": str(row["型号"]).strip() if pd.notna(row["型号"]) else None,
            "manufacturer": str(row["制造商"]).strip() if pd.notna(row["制造商"]) else None,
            "commissioning_date": row["启用日期"] if pd.notna(row["启用日期"]) else None,
        }

        if target_equip:
            for field, new_val in new_vals.items():
                old_val = getattr(target_equip, field, None)
                if old_val != new_val:
                    changes_log.append({"asset_no": asset_no, "field": field, "old": str(old_val), "new": str(new_val)})

            if not dry_run:
                await db.execute(update(Equipment).where(Equipment.id == target_equip.id).values(**new_vals))
            processed_ids.add(target_equip.id)
            updated += 1
        elif asset_no in asset_index:
            # 真正的迁移：资产号存在但部门/位置都变了
            old_equip = asset_index[asset_no][0]
            if not dry_run:
                await db.execute(update(Equipment).where(Equipment.id == old_equip.id).values(**new_vals))
            processed_ids.add(old_equip.id)
            migrated += 1
        else:
            if not dry_run:
                db.add(Equipment(asset_no=asset_no, is_deleted=False, **new_vals))
            inserted += 1

    # 熔断检查
    active_asset_nos = {e.asset_no for e in all_active}
    excel_asset_nos = set(df["资产编号"].dropna().astype(str).str.strip())
    missing_assets = active_asset_nos - excel_asset_nos

    if len(active_asset_nos) > 0 and len(missing_assets) / len(active_asset_nos) > MISSING_ASSET_THRESHOLD:
        raise ValueError(
            f"安全熔断：Excel 中缺失 {len(missing_assets)} 台在用设备（占比 > 5%），请确认是否上传了错误的文件！"
        )

    for e in all_active:
        if e.id not in processed_ids:
            if not dry_run:
                await db.execute(update(Equipment).where(Equipment.id == e.id).values(is_deleted=True))
            deleted += 1
            changes_log.append({"asset_no": e.asset_no, "field": "status", "old": "Active", "new": "Deleted"})

    if not dry_run:
        log_entry = EquipmentSyncLog(
            operator_id=operator_id,
            file_name=file_name,
            summary={"updated": updated, "inserted": inserted, "migrated": migrated, "deleted": deleted},
            changes_detail=changes_log[:MAX_CHANGES_LOG_ENTRIES],
            is_dry_run=False,
        )
        db.add(log_entry)
        await db.commit()

    return EquipmentSyncResult(
        updated=updated, inserted=inserted, migrated=migrated, deleted=deleted, warnings=warnings
    )


class EquipmentUpdateValues(TypedDict, total=False):
    """设备同步更新值的类型定义"""

    name: str
    current_cost: float | None
    book_value: float | None
    department_id: uuid.UUID | None
    location_id: uuid.UUID | None
    location_text: str | None
    model: str | None
    manufacturer: str | None
    commissioning_date: datetime.date | None
