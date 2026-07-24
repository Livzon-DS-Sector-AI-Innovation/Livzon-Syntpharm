"""设备导入 API 路由."""

import uuid
from datetime import date, datetime
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import success_response
from app.modules.equipment import repository as repo

router = APIRouter()


# 列名映射：支持多种常见的列名变体
COLUMN_MAPPING = {
    "资产编号": ["资产编号", "编号", "资产号", "Asset No", "AssetNo"],
    "标签号": ["标签号", "标签", "Label No", "LabelNo"],
    "设备位号": ["设备位号", "位号", "Tag No", "TagNo", "Equipment Tag"],
    "资产说明": ["资产说明", "设备名称", "名称", "Name", "Description"],
    "设备分类": ["设备分类", "分类", "Class", "Equipment Class"],
    "资产类别说明": ["资产类别说明", "类别", "Category", "资产类别"],
    "制造商": ["制造商", "厂家", "Manufacturer"],
    "型号": ["型号", "规格型号", "Model"],
    "设备规格": ["设备规格", "规格", "Specification", "Spec"],
    "供应商": ["供应商", "供货商", "Supplier", "Vendor"],
    "当前成本": ["当前成本", "成本", "金额", "价值", "Value", "Cost"],
    "出厂日期": ["出厂日期", "生产日期", "制造日期", "Production Date"],
    "启用日期": ["启用日期", "投入使用日期", "启用时间", "Commissioning Date"],
    "实物所在部门": ["实物所在部门", "部门", "使用部门", "Department"],
    "实物所在地点": ["实物所在地点", "地点", "位置", "存放地点", "Location"],
    "负责人": ["负责人", "责任人", "负责人姓名", "Responsible Person"],
    "报废状态": ["报废状态", "状态", "Status"],
    "报废时间": ["报废时间", "报废日期", "Scrap Date"],
    "账面净值": ["账面净值", "帐面净值", "净值", "账面价值", "帐面价值", "Book Value", "BookValue"],
}


def get_column_value(row: dict, field_name: str) -> any:
    """从行数据中获取字段值，支持多种列名变体"""
    possible_names = COLUMN_MAPPING.get(field_name, [field_name])
    for name in possible_names:
        if name in row:
            return row[name]
    return None


# 部门映射表：Excel 部门名称 → 飞书部门名称
DEPT_MAPPING = {
    # 直接映射
    "仪表电工班": "设备工程部",
    "工程部": "设备工程部",
    "制冷班": "动力部",
    "锅炉制水班": "动力部",
    "机修班": "动力部",
    "实验室": "技术研发部",
    "检验室": "质量控制部",
    "质量部": "质量保证部",
    "生产管理部": "生产部",
    "头孢精制制造部": "头孢无菌制造部",
    # 车间映射
    "头孢合成一车间": "201车间",
    "头孢合成二车间": "202车间",
    "头孢精制一车间": "301车间",
    "头孢精制二车间": "302车间",
    "头孢精制三车间": "303车间",
    "非头孢一车间": "101车间",
    "非头孢二车间": "102车间",
    "非头孢三车间": "103车间",
    "非头孢五车间": "105车间",
    "非头孢六车间": "106车间",
    "非头孢七车间": "107车间",
}


def map_department_name(excel_dept: str) -> tuple[str | None, str | None]:
    """
    映射 Excel 部门名称到飞书部门名称

    Returns:
        (dept_name, location_text): 部门名称和地点文本
    """
    if not excel_dept:
        return None, None

    # 特殊处理：溶剂回收车间-XXX岗
    if excel_dept.startswith("溶剂回收车间-"):
        gang = excel_dept.replace("溶剂回收车间-", "")
        return "溶剂回收车间", gang

    # 查映射表
    mapped_name = DEPT_MAPPING.get(excel_dept, excel_dept)
    return mapped_name, None


async def get_department_id_by_name(db: AsyncSession, dept_name: str) -> uuid.UUID | None:
    """根据部门名称查询部门 ID"""
    if not dept_name:
        return None

    from sqlalchemy import select

    from app.platform.identity.models import Department

    result = await db.execute(
        select(Department.id).where(
            Department.name == dept_name,
            Department.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


def parse_excel_date(value: Any) -> date | None:
    """解析 Excel 日期（可能是数字或字符串）"""
    if not value:
        return None

    # 如果是数字（Excel 日期序列号）
    if isinstance(value, (int, float)):
        # Excel 日期序列号从 1900-01-01 开始
        from datetime import timedelta

        base_date = date(1899, 12, 30)
        return base_date + timedelta(days=int(value))

    # 如果是字符串
    if isinstance(value, str):
        for fmt in ["%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"]:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

    return None


def map_equipment_class_raw(equipment_class_raw: str) -> str | None:
    """映射设备分类（A/B/C）"""
    if not equipment_class_raw:
        return None
    equipment_class_raw = equipment_class_raw.strip().upper()
    if equipment_class_raw in ["A", "B", "C"]:
        return equipment_class_raw
    return None


def map_equipment_class(category_desc: str) -> str:
    """映射资产类别到设备分类（A/B/C）"""
    if not category_desc:
        return "C"

    # 简单映射逻辑，可根据实际需求调整
    if "机器设备" in category_desc:
        return "A"
    elif "电子设备" in category_desc:
        return "B"
    else:
        return "C"


def map_scrap_status(status: str) -> tuple[str, str]:
    """映射报废状态到设备状态"""
    if status == "已报废":
        return "报废", "已报废"
    else:
        return "在用", "未报废"


@router.post("/preview", summary="预览导入数据")
async def preview_import(
    data: list[dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> dict:
    """
    预览导入数据，返回转换后的结果（不入库）

    数据格式（来自 Excel）：
    [
        {
            "资产编号": "59070",
            "标签号": "107001252",
            "资产说明": "生化培养箱",
            "资产类别说明": "固定资产.电子设备",
            "制造商": "重庆永生",
            "型号": "SHH-L",
            "当前成本": 22123.89,
            "启用日期": 46196.0,
            "实物所在部门": "检验室",
            "实物所在地点": "微生物室",
            "报废状态": "未报废",
            "报废时间": ""
        }
    ]
    """
    preview_items = []

    for idx, row in enumerate(data):
        # 提取字段
        asset_no = str(get_column_value(row, "资产编号") or "").strip()
        label_no = str(get_column_value(row, "标签号") or "").strip() or None
        equipment_tag = str(get_column_value(row, "设备位号") or "").strip() or None
        name = str(get_column_value(row, "资产说明") or "").strip()
        equipment_class_raw = str(get_column_value(row, "设备分类") or "").strip()
        category_desc = str(get_column_value(row, "资产类别说明") or "").strip()
        manufacturer = str(get_column_value(row, "制造商") or "").strip() or None
        model = str(get_column_value(row, "型号") or "").strip() or None
        specification = str(get_column_value(row, "设备规格") or "").strip() or None
        supplier = str(get_column_value(row, "供应商") or "").strip() or None
        current_cost = get_column_value(row, "当前成本")
        book_value = get_column_value(row, "账面净值")
        production_date_raw = get_column_value(row, "出厂日期")
        commissioning_date_raw = get_column_value(row, "启用日期")
        excel_dept = str(get_column_value(row, "实物所在部门") or "").strip()
        excel_location = str(get_column_value(row, "实物所在地点") or "").strip()
        responsible_person = str(get_column_value(row, "负责人") or "").strip() or None
        scrap_status_raw = str(get_column_value(row, "报废状态") or "").strip()
        scrap_time_raw = get_column_value(row, "报废时间")

        # 映射部门
        mapped_dept_name, location_from_dept = map_department_name(excel_dept)
        dept_id = await get_department_id_by_name(db, mapped_dept_name) if mapped_dept_name else None

        # 地点：优先使用从部门映射的地点，否则使用 Excel 的地点列
        location_text = excel_location or location_from_dept or None

        # 映射状态
        status, scrap_status = map_scrap_status(scrap_status_raw)

        # 解析日期
        production_date = parse_excel_date(production_date_raw)
        commissioning_date = parse_excel_date(commissioning_date_raw)
        scrap_time = parse_excel_date(scrap_time_raw)

        # 映射设备分类
        equipment_class = map_equipment_class_raw(equipment_class_raw) or map_equipment_class(category_desc)

        # 构建预览项
        preview_item = {
            "row_index": idx,
            "asset_no": asset_no,
            "label_no": label_no,
            "equipment_tag": equipment_tag,
            "name": name,
            "equipment_class": equipment_class,
            "category_description": category_desc or None,
            "manufacturer": manufacturer,
            "model": model,
            "specification": specification,
            "supplier": supplier,
            "current_cost": current_cost,
            "book_value": book_value,
            "production_date": production_date.isoformat() if production_date else None,
            "commissioning_date": commissioning_date.isoformat() if commissioning_date else None,
            "department_name": mapped_dept_name,
            "department_id": str(dept_id) if dept_id else None,
            "location_text": location_text,
            "responsible_person_name": responsible_person,
            "status": status,
            "scrap_status": scrap_status,
            "scrap_time": scrap_time.isoformat() if scrap_time else None,
            "validation_errors": [],
        }

        # 验证必填字段
        if not asset_no:
            preview_item["validation_errors"].append("资产编号不能为空")
        if not name:
            preview_item["validation_errors"].append("设备名称不能为空")

        # 检查部门是否存在
        if mapped_dept_name and not dept_id:
            preview_item["validation_errors"].append(f"部门 '{mapped_dept_name}' 在系统中不存在")

        preview_items.append(preview_item)

    # 统计
    valid_count = sum(1 for item in preview_items if not item["validation_errors"])
    invalid_count = len(preview_items) - valid_count

    return success_response(
        data={
            "total": len(preview_items),
            "valid_count": valid_count,
            "invalid_count": invalid_count,
            "items": preview_items,
        }
    )


@router.post("/batch", summary="批量导入设备")
async def batch_import(
    data: list[dict[str, Any]],
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser = None,
) -> dict:
    """
    批量导入设备（先预览，再导入）

    数据格式同 preview 接口
    """
    created_count = 0
    skipped_count = 0
    errors = []

    for idx, row in enumerate(data):
        try:
            # 提取字段
            asset_no = str(get_column_value(row, "资产编号") or "").strip()
            label_no = str(get_column_value(row, "标签号") or "").strip() or None
            equipment_tag = str(get_column_value(row, "设备位号") or "").strip() or None
            name = str(get_column_value(row, "资产说明") or "").strip()
            equipment_class_raw = str(get_column_value(row, "设备分类") or "").strip()
            category_desc = str(get_column_value(row, "资产类别说明") or "").strip()
            manufacturer = str(get_column_value(row, "制造商") or "").strip() or None
            model = str(get_column_value(row, "型号") or "").strip() or None
            specification = str(get_column_value(row, "设备规格") or "").strip() or None
            supplier = str(get_column_value(row, "供应商") or "").strip() or None
            current_cost = get_column_value(row, "当前成本")
            book_value = get_column_value(row, "账面净值")
            production_date_raw = get_column_value(row, "出厂日期")
            commissioning_date_raw = get_column_value(row, "启用日期")
            excel_dept = str(get_column_value(row, "实物所在部门") or "").strip()
            excel_location = str(get_column_value(row, "实物所在地点") or "").strip()
            responsible_person = str(get_column_value(row, "负责人") or "").strip() or None
            scrap_status_raw = str(get_column_value(row, "报废状态") or "").strip()
            scrap_time_raw = get_column_value(row, "报废时间")

            # 验证必填字段
            if not asset_no or not name:
                skipped_count += 1
                errors.append({"row": idx, "error": "资产编号或设备名称为空"})
                continue

            # 映射部门
            mapped_dept_name, location_from_dept = map_department_name(excel_dept)
            dept_id = await get_department_id_by_name(db, mapped_dept_name) if mapped_dept_name else None

            # 地点
            location_text = excel_location or location_from_dept or None

            # 映射状态
            status, scrap_status = map_scrap_status(scrap_status_raw)

            # 解析日期
            production_date = parse_excel_date(production_date_raw)
            commissioning_date = parse_excel_date(commissioning_date_raw)
            scrap_time = parse_excel_date(scrap_time_raw)

            # 映射设备分类
            equipment_class = map_equipment_class_raw(equipment_class_raw) or map_equipment_class(category_desc)

            # 创建设备
            equipment_data = {
                "asset_no": asset_no,
                "label_no": label_no,
                "equipment_tag": equipment_tag,
                "name": name,
                "equipment_class": equipment_class,
                "category_description": category_desc or None,
                "manufacturer": manufacturer,
                "model": model,
                "specification": specification,
                "supplier": supplier,
                "current_cost": current_cost,
                "book_value": book_value,
                "production_date": production_date,
                "commissioning_date": commissioning_date,
                "department_id": dept_id,
                "location_text": location_text,
                "responsible_person_name": responsible_person,
                "status": status,
                "scrap_status": scrap_status,
                "scrap_time": scrap_time,
                "importance": "中",
            }

            equipment = await repo.create_equipment(db, equipment_data)
            # 每行独立 commit，确保成功的数据立即保存
            await db.commit()
            created_count += 1

        except Exception as e:
            # 失败时 rollback 当前事务，继续处理下一行
            await db.rollback()
            skipped_count += 1
            errors.append({"row": idx, "error": str(e)})

    return success_response(
        data={
            "created_count": created_count,
            "skipped_count": skipped_count,
            "errors": errors,
        }
    )
