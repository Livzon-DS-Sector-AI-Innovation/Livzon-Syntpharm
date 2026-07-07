"""原料报告单 API"""

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.core.database import get_db, AsyncSession
from app.core.storage import save_upload_file
from app.modules.quality.qms.material_report_service import (
    MaterialReportService,
    ReportTemplateService,
)
from app.modules.quality.qms.material_report_schemas import (
    ReportCreate,
    ReportUpdate,
    ReportItemsBatchSave,
    ReportFilter,
    TemplateCreate,
    TemplateUpdate,
)


class ApiResponse(BaseModel):
    """统一响应格式"""
    code: int = 200
    message: str = "Success"
    data: Optional[dict | list] = None


router = APIRouter(prefix="/quality/material-report", tags=["原料报告单"])


# ============ 报告单 API ============

@router.get("/", summary="获取报告单列表")
async def list_reports(
    template_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """获取报告单列表"""
    service = MaterialReportService(session)

    # 解析UUID
    template_uuid = None
    if template_id:
        try:
            template_uuid = UUID(template_id)
        except ValueError:
            pass

    reports, total = await service.list_reports(
        template_id=template_uuid,
        status=status,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data={
            "items": reports,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/", summary="创建报告单")
async def create_report(
    data: ReportCreate,
    session: AsyncSession = Depends(get_db),
):
    """创建报告单"""
    service = MaterialReportService(session)
    report = await service.create_report(data)
    return ApiResponse(data={"id": str(report.id), "report_no": report.report_no})


@router.get("/statistics", summary="获取统计数据")
async def get_statistics(
    session: AsyncSession = Depends(get_db),
):
    """获取统计数据"""
    service = MaterialReportService(session)
    stats = await service.get_statistics()
    return ApiResponse(data=stats)


@router.get("/{report_id}", summary="获取报告单详情")
async def get_report(
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """获取报告单详情"""
    service = MaterialReportService(session)
    report = await service.get_report(report_id)

    if not report:
        raise HTTPException(status_code=404, detail="报告单不存在")

    return ApiResponse(data=report)


@router.put("/{report_id}", summary="更新报告单")
async def update_report(
    report_id: UUID,
    data: ReportUpdate,
    session: AsyncSession = Depends(get_db),
):
    """更新报告单"""
    service = MaterialReportService(session)
    report = await service.update_report(report_id, data)

    if not report:
        raise HTTPException(status_code=404, detail="报告单不存在")

    return ApiResponse(data=report)


@router.delete("/{report_id}", summary="删除报告单")
async def delete_report(
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """删除报告单"""
    service = MaterialReportService(session)
    success = await service.delete_report(report_id)

    if not success:
        raise HTTPException(status_code=404, detail="报告单不存在")

    return ApiResponse(message="删除成功")


@router.post("/{report_id}/items", summary="批量保存明细数据")
async def save_items(
    report_id: UUID,
    data: ReportItemsBatchSave,
    session: AsyncSession = Depends(get_db),
):
    """批量保存明细数据"""
    service = MaterialReportService(session)

    # 检查报告单是否存在
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告单不存在")

    items = await service.save_items(report_id, data)
    return ApiResponse(data={"items": items})


@router.post("/{report_id}/generate", summary="生成报告单文件")
async def generate_report(
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """生成报告单Word文件并下载"""
    service = MaterialReportService(session)

    try:
        content = await service.generate_report(report_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 获取报告单信息用于文件名
    report = await service.get_report(report_id)
    filename = f"{report['report_no']}.docx"

    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{filename}"
        },
    )


@router.post("/{report_id}/submit", summary="提交报告单")
async def submit_report(
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """提交报告单"""
    service = MaterialReportService(session)

    try:
        report = await service.submit_report(report_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return ApiResponse(data=report)


# ============ 模板管理 API ============

@router.get("/template/", summary="获取模板列表")
async def list_templates(
    is_active: Optional[bool] = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
):
    """获取模板列表"""
    service = ReportTemplateService(session)
    templates, total = await service.list_templates(
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    return ApiResponse(
        data={
            "items": templates,
            "total": total,
            "page": page,
            "page_size": page_size,
        }
    )


@router.post("/template/", summary="上传Word模板")
async def upload_template(
    file: UploadFile = File(..., description="Word模板文件"),
    template_name: str = Form(..., description="模板名称"),
    template_description: Optional[str] = Form(None, description="模板描述"),
    field_mapping: Optional[str] = Form(None, description="静态字段映射JSON"),
    table_fields: Optional[str] = Form(None, description="动态表格字段JSON"),
    session: AsyncSession = Depends(get_db),
):
    """上传Word模板"""
    # 验证文件类型
    if not file.filename.endswith((".docx", ".doc")):
        raise HTTPException(status_code=400, detail="仅支持Word文档(.docx, .doc)")

    # 保存文件
    file_url = await save_upload_file(file, sub_dir="report-templates")

    # 解析JSON字段
    import json
    field_mapping_dict = {}
    table_fields_dict = {}

    if field_mapping:
        try:
            field_mapping_dict = json.loads(field_mapping)
        except json.JSONDecodeError:
            pass

    if table_fields:
        try:
            table_fields_dict = json.loads(table_fields)
        except json.JSONDecodeError:
            pass

    # 创建模板
    service = ReportTemplateService(session)
    template = await service.create_template(
        TemplateCreate(
            template_name=template_name,
            template_description=template_description,
            field_mapping=field_mapping_dict,
            table_fields=table_fields_dict,
        ),
        file_url=file_url,
    )

    return ApiResponse(data=template)


@router.get("/template/{template_id}", summary="获取模板详情")
async def get_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """获取模板详情"""
    service = ReportTemplateService(session)
    template = await service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return ApiResponse(data=template)


@router.put("/template/{template_id}", summary="更新模板")
async def update_template(
    template_id: UUID,
    data: TemplateUpdate,
    session: AsyncSession = Depends(get_db),
):
    """更新模板"""
    service = ReportTemplateService(session)
    template = await service.update_template(template_id, data)

    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    return ApiResponse(data=template)


@router.delete("/template/{template_id}", summary="删除模板")
async def delete_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """删除模板"""
    service = ReportTemplateService(session)
    success = await service.delete_template(template_id)

    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")

    return ApiResponse(message="删除成功")


@router.get("/template/{template_id}/preview", summary="预览模板字段")
async def preview_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """解析模板获取字段配置"""
    service = ReportTemplateService(session)
    result = await service.parse_template(template_id)

    if not result:
        raise HTTPException(status_code=404, detail="模板不存在")

    return ApiResponse(data=result)


# ============ 图片上传与AI识别 API ============

@router.post("/{report_id}/images", summary="上传图片并AI识别")
async def upload_image_and_recognize(
    report_id: UUID,
    field_key: Optional[str] = Form(None, description="对应字段key"),
    row_index: Optional[int] = Form(None, description="对应行序号"),
    file: UploadFile = File(..., description="图片文件"),
    session: AsyncSession = Depends(get_db),
):
    """上传图片并进行AI识别"""
    service = MaterialReportService(session)

    # 检查报告单是否存在
    report = await service.get_report(report_id)
    if not report:
        raise HTTPException(status_code=404, detail="报告单不存在")

    try:
        result = await service.upload_image_and_recognize(
            report_id=report_id,
            field_key=field_key,
            row_index=row_index,
            file=file,
        )
        return ApiResponse(data=result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{report_id}/images", summary="获取报告单图片列表")
async def get_report_images(
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
):
    """获取报告单的所有图片记录"""
    service = MaterialReportService(session)
    images = await service.get_report_images(report_id)
    return ApiResponse(data=images)