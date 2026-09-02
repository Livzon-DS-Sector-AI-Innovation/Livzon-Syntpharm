"""Equipment database queries live here."""

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.equipment.models import (
    Equipment,
    EquipmentCategory,
    EquipmentCategoryLink,
    Location,
)
from app.platform.identity.models import User


def _escape_like(value: str) -> str:
    """Escape special characters in LIKE patterns."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


# ==================== 设备分类 ====================
async def exists_category_by_code(
    db: AsyncSession,
    code: str,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    """Check if category code exists."""
    query = select(EquipmentCategory.id).where(
        EquipmentCategory.code == code,
        EquipmentCategory.is_deleted.is_(False),  # noqa: E712
    )
    if exclude_id:
        query = query.where(EquipmentCategory.id != exclude_id)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def exists_location_by_code(
    db: AsyncSession,
    code: str,
    exclude_id: uuid.UUID | None = None,
) -> bool:
    """Check if location code exists."""
    query = select(Location.id).where(
        Location.code == code,
        Location.is_deleted.is_(False),  # noqa: E712
    )
    if exclude_id:
        query = query.where(Location.id != exclude_id)
    result = await db.execute(query.limit(1))
    return result.scalar_one_or_none() is not None


async def create_equipment_category(
    db: AsyncSession,
    data: dict[str, Any],
) -> EquipmentCategory:
    """创建设备分类"""
    category = EquipmentCategory(**data)
    db.add(category)
    await db.flush()
    return category


async def get_equipment_category_by_id(
    db: AsyncSession,
    category_id: uuid.UUID,
) -> EquipmentCategory | None:
    """根据ID获取设备分类"""
    result = await db.execute(
        select(EquipmentCategory).where(
            EquipmentCategory.id == category_id,
            EquipmentCategory.is_deleted.is_(False),  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_equipment_categories(
    db: AsyncSession,
    parent_id: uuid.UUID | None = None,
) -> list[EquipmentCategory]:
    """获取设备分类列表"""
    query = select(EquipmentCategory).where(
        EquipmentCategory.is_deleted.is_(False)  # noqa: E712
    )
    if parent_id is not None:
        query = query.where(EquipmentCategory.parent_id == parent_id)
    else:
        query = query.where(EquipmentCategory.parent_id.is_(None))
    query = query.order_by(EquipmentCategory.code)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_equipment_category_tree(db: AsyncSession) -> list[EquipmentCategory]:
    """获取设备分类树形结构"""
    result = await db.execute(
        select(EquipmentCategory)
        .where(EquipmentCategory.is_deleted.is_(False))  # noqa: E712
        .options(selectinload(EquipmentCategory.children))
        .order_by(EquipmentCategory.code)
    )
    categories = list(result.scalars().all())

    category_map: dict[uuid.UUID, EquipmentCategory] = {cat.id: cat for cat in categories}
    for category in categories:
        category.children = []
    root_categories: list[EquipmentCategory] = []

    for category in categories:
        if category.parent_id is None:
            root_categories.append(category)
        else:
            parent = category_map.get(category.parent_id)
            if parent:
                parent.children.append(category)

    return root_categories


async def update_equipment_category(
    db: AsyncSession,
    category_id: uuid.UUID,
    data: dict[str, Any],
) -> EquipmentCategory | None:
    """更新设备分类"""
    category = await get_equipment_category_by_id(db, category_id)
    if not category:
        return None
    for key, value in data.items():
        setattr(category, key, value)
    await db.flush()
    await db.refresh(category)
    return category


async def delete_equipment_category(
    db: AsyncSession,
    category_id: uuid.UUID,
) -> bool:
    """删除设备分类（软删除）"""
    category = await get_equipment_category_by_id(db, category_id)
    if not category:
        return False
    category.is_deleted = True
    await db.flush()
    return True


# ==================== 位置管理 ====================
async def create_location(
    db: AsyncSession,
    data: dict[str, Any],
) -> Location:
    """创建位置"""
    location = Location(**data)
    db.add(location)
    await db.flush()
    return location


async def get_location_by_id(
    db: AsyncSession,
    location_id: uuid.UUID,
) -> Location | None:
    """根据ID获取位置"""
    result = await db.execute(
        select(Location).where(
            Location.id == location_id,
            Location.is_deleted.is_(False),  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_locations(
    db: AsyncSession,
    parent_id: uuid.UUID | None = None,
) -> list[Location]:
    """获取位置列表"""
    query = select(Location).where(Location.is_deleted.is_(False))  # noqa: E712
    if parent_id is not None:
        query = query.where(Location.parent_id == parent_id)
    else:
        query = query.where(Location.parent_id.is_(None))
    query = query.order_by(Location.code)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_location_tree(db: AsyncSession) -> list[Location]:
    """获取位置树形结构"""
    result = await db.execute(
        select(Location)
        .where(Location.is_deleted.is_(False))  # noqa: E712
        .options(selectinload(Location.children))
        .order_by(Location.code)
    )
    locations = list(result.scalars().all())

    location_map: dict[uuid.UUID, Location] = {loc.id: loc for loc in locations}
    for location in locations:
        location.children = []
    root_locations: list[Location] = []

    for location in locations:
        if location.parent_id is None:
            root_locations.append(location)
        else:
            parent = location_map.get(location.parent_id)
            if parent:
                parent.children.append(location)

    return root_locations


async def update_location(
    db: AsyncSession,
    location_id: uuid.UUID,
    data: dict[str, Any],
) -> Location | None:
    """更新位置"""
    location = await get_location_by_id(db, location_id)
    if not location:
        return None
    for key, value in data.items():
        setattr(location, key, value)
    await db.flush()
    await db.refresh(location)
    return location


async def delete_location(
    db: AsyncSession,
    location_id: uuid.UUID,
) -> bool:
    """删除位置（软删除）"""
    location = await get_location_by_id(db, location_id)
    if not location:
        return False
    location.is_deleted = True
    await db.flush()
    return True


async def _get_category_child_ids(
    db: AsyncSession,
    parent_id: uuid.UUID,
) -> list[uuid.UUID]:
    """递归收集指定分类及其所有子孙分类的ID"""
    result = await db.execute(
        select(EquipmentCategory.id).where(
            EquipmentCategory.parent_id == parent_id,
            EquipmentCategory.is_deleted.is_(False),  # noqa: E712
        )
    )
    child_ids = list(result.scalars().all())
    all_ids: list[uuid.UUID] = [parent_id]
    for child_id in child_ids:
        all_ids.extend(await _get_category_child_ids(db, child_id))
    return all_ids


async def _get_location_child_ids(
    db: AsyncSession,
    parent_id: uuid.UUID,
) -> list[uuid.UUID]:
    """递归收集指定位置及其所有子孙位置的ID"""
    result = await db.execute(
        select(Location.id).where(
            Location.parent_id == parent_id,
            Location.is_deleted.is_(False),  # noqa: E712
        )
    )
    child_ids = list(result.scalars().all())
    all_ids: list[uuid.UUID] = [parent_id]
    for child_id in child_ids:
        all_ids.extend(await _get_location_child_ids(db, child_id))
    return all_ids


# ==================== 设备管理 ====================
async def create_equipment(
    db: AsyncSession,
    data: dict[str, Any],
    category_ids: list[uuid.UUID] | None = None,
) -> Equipment:
    """创建设备"""
    # 提取 category_ids，不传给 Equipment 构造
    cids = category_ids if category_ids is not None else data.pop("category_ids", None) or []

    # 清理同 asset_no 的已软删除记录，避免重复添加→删除→添加→删除时违反唯一约束
    asset_no = data.get("asset_no")
    if asset_no:
        deleted_result = await db.execute(
            select(Equipment).where(
                Equipment.asset_no == asset_no,
                Equipment.is_deleted.is_(True),  # noqa: E712
            )
        )
        for old in deleted_result.scalars().all():
            await db.delete(old)

    equipment = Equipment(**data)
    db.add(equipment)
    await db.flush()

    # 创建分类关联（去重）
    seen: set[uuid.UUID] = set()
    for cid in cids:
        if cid not in seen:
            seen.add(cid)
            db.add(EquipmentCategoryLink(equipment_id=equipment.id, category_id=cid))
    await db.flush()

    # eager re-fetch
    return await _refetch_equipment(db, equipment.id)  # type: ignore[return-value]


async def _refetch_equipment(db: AsyncSession, equipment_id: uuid.UUID) -> Equipment | None:
    """eager re-fetch 设备及关联"""
    result = await db.execute(
        select(Equipment)
        .options(
            selectinload(Equipment.category_links).selectinload(EquipmentCategoryLink.category),
            selectinload(Equipment.location),
        )
        .where(Equipment.id == equipment_id, not Equipment.is_deleted)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def get_equipment_by_id(
    db: AsyncSession,
    equipment_id: uuid.UUID,
) -> Equipment | None:
    """根据ID获取设备"""
    result = await db.execute(
        select(Equipment)
        .options(
            selectinload(Equipment.category_links).selectinload(EquipmentCategoryLink.category),
            selectinload(Equipment.location),
        )
        .where(
            Equipment.id == equipment_id,
            not Equipment.is_deleted,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_equipment_by_asset_no(
    db: AsyncSession,
    asset_no: str,
) -> Equipment | None:
    """根据资产编号获取设备"""
    result = await db.execute(
        select(Equipment).where(
            Equipment.asset_no == asset_no,
            not Equipment.is_deleted,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


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
    query = (
        select(Equipment)
        .options(
            selectinload(Equipment.category_links).selectinload(EquipmentCategoryLink.category),
            selectinload(Equipment.location),
        )
        .where(not Equipment.is_deleted)  # noqa: E712
    )

    if category_id:
        category_ids = await _get_category_child_ids(db, category_id)
        query = query.where(
            Equipment.id.in_(
                select(EquipmentCategoryLink.equipment_id).where(
                    EquipmentCategoryLink.category_id.in_(category_ids),
                    EquipmentCategoryLink.is_deleted.is_(False),  # noqa: E712
                )
            )
        )
    if location_id:
        location_ids = await _get_location_child_ids(db, location_id)
        query = query.where(Equipment.location_id.in_(location_ids))
    if department_id:
        query = query.where(Equipment.department_id == department_id)
    if status:
        query = query.where(Equipment.status == status)
    if keyword:
        escaped = _escape_like(keyword)
        query = query.where(
            Equipment.asset_no.ilike(f"%{escaped}%", escape="\\")
            | Equipment.name.ilike(f"%{escaped}%", escape="\\")
            | Equipment.equipment_tag.ilike(f"%{escaped}%", escape="\\")
        )

    # 获取总数
    count_query = select(func.count()).select_from(query.with_only_columns(Equipment.id).subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # 分页查询
    query = query.order_by(Equipment.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    equipments = list(result.scalars().all())

    return equipments, total


async def update_equipment(
    db: AsyncSession,
    equipment_id: uuid.UUID,
    data: dict[str, Any],
    category_ids: list[uuid.UUID] | None = None,
) -> Equipment | None:
    """更新设备"""
    equipment = await get_equipment_by_id(db, equipment_id)
    if not equipment:
        return None

    # 提取 category_ids
    cids = category_ids if category_ids is not None else data.pop("category_ids", None)

    for key, value in data.items():
        setattr(equipment, key, value)
    await db.flush()

    # 更新分类关联
    if cids is not None:
        # 去重
        cids = list(dict.fromkeys(cids))

        # 查询该设备所有已有的关联（包括软删除的）
        all_existing_result = await db.execute(
            select(EquipmentCategoryLink).where(
                EquipmentCategoryLink.equipment_id == equipment_id,
            )
        )
        existing_links = list(all_existing_result.scalars().all())
        existing_by_cid: dict[uuid.UUID, EquipmentCategoryLink] = {link.category_id: link for link in existing_links}

        new_cid_set = set(cids)

        for link in existing_links:
            if link.category_id in new_cid_set:
                # 在新列表中：恢复（如果被软删除）或保持不变
                if link.is_deleted:
                    link.is_deleted = False
            else:
                # 不在新列表中：软删除
                if not link.is_deleted:
                    link.is_deleted = True

        # 创建新的关联（之前不存在的分类）
        for cid in cids:
            if cid not in existing_by_cid:
                db.add(EquipmentCategoryLink(equipment_id=equipment_id, category_id=cid))

        await db.flush()

    return await _refetch_equipment(db, equipment_id)


async def delete_equipment(
    db: AsyncSession,
    equipment_id: uuid.UUID,
) -> bool:
    """删除设备（软删除）"""
    equipment = await get_equipment_by_id(db, equipment_id)
    if not equipment:
        return False
    equipment.is_deleted = True

    # 同步软删除设备的所有分类关联，避免分类删除时误判为有设备关联
    links_result = await db.execute(
        select(EquipmentCategoryLink).where(
            EquipmentCategoryLink.equipment_id == equipment_id,
            EquipmentCategoryLink.is_deleted.is_(False),  # noqa: E712
        )
    )
    for link in links_result.scalars().all():
        link.is_deleted = True

    await db.flush()
    return True


async def count_equipments_by_category(
    db: AsyncSession,
    category_id: uuid.UUID,
) -> int:
    """统计指定分类下的设备数量（通过联结表）"""
    result = await db.execute(
        select(func.count(func.distinct(EquipmentCategoryLink.equipment_id)))
        .select_from(EquipmentCategoryLink)
        .join(Equipment, Equipment.id == EquipmentCategoryLink.equipment_id)
        .where(
            EquipmentCategoryLink.category_id == category_id,
            EquipmentCategoryLink.is_deleted.is_(False),  # noqa: E712
            not Equipment.is_deleted,  # noqa: E712
        )
    )
    return result.scalar() or 0


async def count_equipments_by_location(
    db: AsyncSession,
    location_id: uuid.UUID,
) -> int:
    """统计指定位置下的设备数量"""
    result = await db.execute(
        select(func.count())
        .select_from(Equipment)
        .where(
            Equipment.location_id == location_id,
            not Equipment.is_deleted,  # noqa: E712
        )
    )
    return result.scalar() or 0


async def get_max_equipment_no_by_category(
    db: AsyncSession,
    category_code: str,
) -> str | None:
    """获取指定分类的最大设备编号"""
    pattern = f"EQ-{category_code}-%"
    result = await db.execute(
        select(Equipment.equipment_tag)
        .where(
            Equipment.equipment_tag.like(pattern),
            not Equipment.is_deleted,  # noqa: E712
        )
        .order_by(Equipment.equipment_tag.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_equipment_statistics(
    db: AsyncSession,
    category_id: uuid.UUID | None = None,
    location_id: uuid.UUID | None = None,
    department_id: uuid.UUID | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """获取设备统计（支持筛选）"""
    # 构建基础查询条件
    base_filter = Equipment.is_deleted.is_(False)  # noqa: E712

    # 添加筛选条件
    if category_id:
        category_ids = await _get_category_child_ids(db, category_id)
        base_filter = base_filter & Equipment.id.in_(
            select(EquipmentCategoryLink.equipment_id).where(
                EquipmentCategoryLink.category_id.in_(category_ids),
                EquipmentCategoryLink.is_deleted.is_(False),  # noqa: E712
            )
        )
    if location_id:
        location_ids = await _get_location_child_ids(db, location_id)
        base_filter = base_filter & Equipment.location_id.in_(location_ids)
    if department_id:
        base_filter = base_filter & (Equipment.department_id == department_id)
    if status:
        base_filter = base_filter & (Equipment.status == status)

    # 总数
    total_result = await db.execute(select(func.count()).where(base_filter))
    total = total_result.scalar() or 0

    # 按状态统计
    status_result = await db.execute(
        select(Equipment.status, func.count()).where(base_filter).group_by(Equipment.status)
    )
    by_status = {row[0]: row[1] for row in status_result.all()}

    # 按分类统计（A/B/C）
    class_result = await db.execute(
        select(Equipment.equipment_class, func.count()).where(base_filter).group_by(Equipment.equipment_class)
    )
    by_category = {row[0]: row[1] for row in class_result.all()}

    # 按位置统计
    location_result = await db.execute(
        select(Location.name, func.count())
        .join(Equipment, Equipment.location_id == Location.id)
        .where(base_filter)
        .group_by(Location.name)
    )
    by_location = {row[0]: row[1] for row in location_result.all()}

    return {
        "total": total,
        "by_status": by_status,
        "by_category": by_category,
        "by_location": by_location,
    }


async def get_departments_for_select(db: AsyncSession) -> list[dict[str, Any]]:
    """获取可选部门列表（含负责人），供下拉使用"""
    from app.modules.hr.public_api import list_all_departments

    departments = await list_all_departments(db)
    # Sort by name and return as dicts
    sorted_depts = sorted(departments, key=lambda d: d.name)
    return [{"id": dept.id, "name": dept.name} for dept in sorted_depts]


async def get_department_info(db: AsyncSession, department_id: uuid.UUID) -> dict[str, Any] | None:
    """获取单个部门信息（含负责人姓名和 leader_id）
    注意：当前 HrDepartment 模型暂无负责人字段，暂时只返回基本信息
    """
    from app.modules.hr.public_api import list_all_departments

    departments = await list_all_departments(db)
    dept = next((d for d in departments if d.id == department_id), None)
    if not dept:
        return None
    row = {"id": dept.id, "name": dept.name}
    d = dict(row)
    d["leader_user_id"] = None
    d["leader_id"] = None
    d["leader_name"] = None
    return d


async def get_department_leader_user_id(db: AsyncSession, department_id: uuid.UUID) -> uuid.UUID | None:
    """获取部门负责人的 User.id（UUID）
    注意：当前 HrDepartment 模型暂无负责人字段，暂时返回 None
    """
    return None


async def get_user_name_by_id(db: AsyncSession, user_id: uuid.UUID) -> str | None:
    """根据 User.id 获取用户姓名"""
    result = await db.execute(select(User.name).where(User.id == user_id))
    return result.scalar_one_or_none()


async def get_sync_context(session) -> tuple[dict, dict, dict, list]:
    """获取同步所需的部门和位置映射及活跃设备索引"""
    # 使用原始 SQL 查询部门数据，避免直接导入 HR 模型
    from sqlalchemy import text

    dept_result = await session.execute(text("SELECT id, name FROM identity.departments WHERE is_deleted = false"))
    dept_map = {n: i for i, n in dept_result.fetchall()}

    loc_result = await session.execute(select(Location.id, Location.name))
    loc_map = {n: i for i, n in loc_result.fetchall()}

    equip_result = await session.execute(select(Equipment).where(not Equipment.is_deleted))
    all_active = equip_result.scalars().all()

    combo_index = {(e.asset_no, e.department_id, e.location_id): e for e in all_active}
    asset_index: dict[str, list] = {}
    for e in all_active:
        asset_index.setdefault(e.asset_no, []).append(e)

    return dept_map, loc_map, all_active, combo_index, asset_index


async def bulk_update_equipment(session, ids_and_vals):
    """批量更新设备"""
    for equip_id, vals in ids_and_vals:
        await session.execute(update(Equipment).where(Equipment.id == equip_id).values(**vals))


async def bulk_insert_equipment(session, equipments):
    """批量新增设备"""
    session.add_all(equipments)


async def bulk_soft_delete(session, ids):
    """批量软删除"""
    for eid in ids:
        await session.execute(update(Equipment).where(Equipment.id == eid).values(is_deleted=True))
