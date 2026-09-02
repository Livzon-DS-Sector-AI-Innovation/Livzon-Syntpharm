"""设备台账 API 路由."""

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import build_response, paginated_response
from app.modules.equipment import repository as repo
from app.modules.equipment import service
from app.modules.equipment.models.equipment import Equipment
from app.modules.equipment.schemas import (
    BatchDeleteRequest,
    EquipmentCategoryCreate,
    EquipmentCategoryResponse,
    EquipmentCategoryTree,
    EquipmentCategoryUpdate,
    EquipmentCreate,
    EquipmentResponse,
    EquipmentStatistics,
    EquipmentUpdate,
    LocationCreate,
    LocationResponse,
    LocationTree,
    LocationUpdate,
)
from app.shared.schemas import ApiResponse

# 文件上传限制
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls"}

RATE_LIMIT_PER_MINUTE = 5  # 每分钟最多 5 次同步请求

# 简单的内存速率限制器（生产环境应使用 Redis）
_rate_limit_store: dict[str, list[float]] = {}


def _check_rate_limit(user_id: str) -> bool:
    """检查用户是否在速率限制内"""
    import time

    now = time.time()
    window = 60  # 60 秒窗口

    if user_id not in _rate_limit_store:
        _rate_limit_store[user_id] = []

    # 清理过期记录
    _rate_limit_store[user_id] = [t for t in _rate_limit_store[user_id] if now - t < window]

    if len(_rate_limit_store[user_id]) >= RATE_LIMIT_PER_MINUTE:
        return False

    _rate_limit_store[user_id].append(now)
    return True


def _validate_excel_signature(content: bytes) -> bool:
    """验证文件是否为有效的 Excel 格式（检查文件签名）"""
    if not content or len(content) < 4:
        return False

    # Excel .xlsx 文件是 ZIP 格式，以 PK 开头
    # Excel .xls 文件是 OLE2 格式，以 D0 CF 11 E0 开头
    if content[:2] == b"PK":  # .xlsx (ZIP)
        return True
    elif content[:4] == b"\xd0\xcf\x11\xe0":  # .xls (OLE2)
        return True

    return False


router = APIRouter()


async def _equipment_to_response(equipment: Equipment, db: AsyncSession | None = None) -> EquipmentResponse:
    """将 ORM Equipment 转为响应对象，填充多分类信息及部门信息"""
    resp = EquipmentResponse.model_validate(equipment)
    # 设置新字段
    resp.asset_no = equipment.asset_no
    resp.equipment_tag = equipment.equipment_tag
    resp.equipment_class = equipment.equipment_class
    resp.location_text = equipment.location_text
    links = getattr(equipment, "category_links", []) or []
    resp.category_ids = [link.category_id for link in links if not link.is_deleted]
    names = [link.category.name for link in links if not link.is_deleted and link.category]
    resp.category_names = "、".join(names) if names else None
    resp.location_name = equipment.location.name if equipment.location else None
    # 填充部门信息
    if equipment.department_id and db:
        dept_info = await repo.get_department_info(db, equipment.department_id)
        if dept_info:
            resp.department_name = dept_info["name"]
            # 负责人：优先用设备独立设置的 responsible_person_name；否则由部门负责人推导
            if not equipment.responsible_person_name:
                resp.responsible_person_name = dept_info.get("leader_name")
                resp.responsible_person_id = dept_info.get("leader_id")
    # 如果设备有独立的 responsible_person_name，直接使用
    if equipment.responsible_person_name:
        resp.responsible_person_name = equipment.responsible_person_name
    return resp


# ==================== 设备分类 ====================
@router.post("/categories", summary="创建设备分类")
async def create_equipment_category(
    data: EquipmentCategoryCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """创建设备分类"""
    category = await service.create_equipment_category(db, data)
    return build_response(data=EquipmentCategoryResponse.model_validate(category))


@router.get("/categories", summary="获取设备分类列表")
async def get_equipment_categories(
    parent_id: uuid.UUID | None = Query(None, description="父分类ID"),
    tree: bool = Query(False, description="是否返回树形结构"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取设备分类列表"""
    if tree:
        categories = await service.get_equipment_category_tree(db)
        return build_response(data=[EquipmentCategoryTree.model_validate(c) for c in categories])
    categories = await service.get_equipment_categories(db, parent_id)
    return build_response(data=[EquipmentCategoryResponse.model_validate(c) for c in categories])


@router.get("/categories/{category_id}", summary="获取设备分类详情")
async def get_equipment_category(
    category_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取设备分类详情"""
    category = await service.get_equipment_category_by_id(db, category_id)
    return build_response(data=EquipmentCategoryResponse.model_validate(category))


@router.put("/categories/{category_id}", summary="更新设备分类")
async def update_equipment_category(
    category_id: uuid.UUID,
    data: EquipmentCategoryUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """更新设备分类"""
    category = await service.update_equipment_category(db, category_id, data)
    return build_response(data=EquipmentCategoryResponse.model_validate(category))


@router.delete("/categories/{category_id}", summary="删除设备分类")
async def delete_equipment_category(
    category_id: uuid.UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """删除设备分类"""
    await service.delete_equipment_category(db, category_id)
    return build_response(message="删除成功")


# ==================== 位置管理 ====================
@router.post("/locations", summary="创建位置")
async def create_location(
    data: LocationCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """创建位置"""
    location = await service.create_location(db, data)
    return build_response(data=LocationResponse.model_validate(location))


@router.get("/locations", summary="获取位置列表")
async def get_locations(
    parent_id: uuid.UUID | None = Query(None, description="父位置ID"),
    tree: bool = Query(False, description="是否返回树形结构"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取位置列表"""
    if tree:
        locations = await service.get_location_tree(db)
        return build_response(data=[LocationTree.model_validate(loc) for loc in locations])
    locations = await service.get_locations(db, parent_id)
    return build_response(data=[LocationResponse.model_validate(loc) for loc in locations])


@router.get("/locations/{location_id}", summary="获取位置详情")
async def get_location(
    location_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取位置详情"""
    location = await service.get_location_by_id(db, location_id)
    return build_response(data=LocationResponse.model_validate(location))


@router.put("/locations/{location_id}", summary="更新位置")
async def update_location(
    location_id: uuid.UUID,
    data: LocationUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """更新位置"""
    location = await service.update_location(db, location_id, data)
    return build_response(data=LocationResponse.model_validate(location))


@router.delete("/locations/{location_id}", summary="删除位置")
async def delete_location(
    location_id: uuid.UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """删除位置"""
    await service.delete_location(db, location_id)
    return build_response(message="删除成功")


# ==================== 部门列表（供设备表单下拉使用） ====================
@router.get("/departments", summary="获取部门列表（供设备表单下拉使用）")
async def get_departments_list(
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取可选部门列表，含部门名称和负责人姓名"""
    departments = await service.get_departments_for_select(db)
    return build_response(data=departments)


# ==================== 设备管理 ====================
@router.post("/equipments", summary="创建设备")
async def create_equipment(
    data: EquipmentCreate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """创建设备"""
    equipment = await service.create_equipment(db, data)
    return build_response(data=await _equipment_to_response(equipment, db))


@router.get("/equipments", summary="获取设备列表")
async def get_equipments(
    category_id: uuid.UUID | None = Query(None, description="设备分类ID"),
    location_id: uuid.UUID | None = Query(None, description="设备位置ID"),
    department_id: uuid.UUID | None = Query(None, description="归属部门ID"),
    status: str | None = Query(None, description="设备状态"),
    keyword: str | None = Query(None, description="关键词搜索"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取设备列表"""
    equipments, total = await service.get_equipments(
        db, category_id, location_id, department_id, status, keyword, page, page_size
    )
    equipment_responses = []
    for e in equipments:
        equipment_responses.append(await _equipment_to_response(e, db))
    return paginated_response(
        data=equipment_responses,
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/equipments/statistics", summary="获取设备统计")
async def get_equipment_statistics(
    category_id: uuid.UUID | None = Query(None, description="设备分类ID"),
    location_id: uuid.UUID | None = Query(None, description="设备位置ID"),
    department_id: uuid.UUID | None = Query(None, description="归属部门ID"),
    status: str | None = Query(None, description="设备状态"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取设备统计（支持筛选）"""
    stats = await service.get_equipment_statistics(db, category_id, location_id, department_id, status)
    return build_response(data=EquipmentStatistics(**stats))


@router.get("/equipments/{equipment_id}", summary="获取设备详情")
async def get_equipment(
    equipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """获取设备详情"""
    equipment = await service.get_equipment_by_id(db, equipment_id)
    return build_response(data=await _equipment_to_response(equipment, db))


@router.put("/equipments/{equipment_id}", summary="更新设备")
async def update_equipment(
    equipment_id: uuid.UUID,
    data: EquipmentUpdate,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """更新设备"""
    equipment = await service.update_equipment(db, equipment_id, data)
    return build_response(data=await _equipment_to_response(equipment, db))


@router.delete("/equipments/{equipment_id}", summary="删除设备")
async def delete_equipment(
    equipment_id: uuid.UUID,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """删除设备"""
    await service.delete_equipment(db, equipment_id)
    return build_response(message="删除成功")


@router.post("/equipments/batch-delete", summary="批量删除设备")
async def batch_delete_equipments(
    data: BatchDeleteRequest,
    current_user: RequiredUser,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """批量删除设备"""
    deleted_count = await service.batch_delete_equipments(db, data.ids)
    return build_response(message=f"成功删除 {deleted_count} 台设备")


@router.post("/equipments/sync-excel", summary="智能同步 Excel 设备数据")
async def sync_equipments_excel(
    current_user: RequiredUser,
    file: UploadFile = File(...),
    dry_run: bool = Query(False, description="是否仅预览不执行"),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """上传 Excel 文件并执行智能同步"""
    # 检查速率限制
    if not _check_rate_limit(str(current_user.id)):
        raise ValueError(f"操作过于频繁，请稍后再试（限制：{RATE_LIMIT_PER_MINUTE} 次/分钟）")

    # 验证文件扩展名
    if not file.filename:
        raise ValueError("文件名不能为空")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXCEL_EXTENSIONS:
        raise ValueError(f"不支持的文件格式: {file_ext}，仅支持 {', '.join(ALLOWED_EXCEL_EXTENSIONS)}")

    # 读取文件内容
    content = await file.read()

    # 验证文件大小
    if len(content) > MAX_FILE_SIZE:
        raise ValueError(
            f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)，当前文件大小: {len(content) // 1024}KB"
        )

    # 验证 MIME 类型（简单检查文件头）
    if not _validate_excel_signature(content):
        raise ValueError("文件内容不是有效的 Excel 格式")
    result = await service.sync_equipments_with_audit(
        db, content, dry_run=dry_run, operator_id=current_user.id, file_name=file.filename
    )
    return build_response(data=result.model_dump())
