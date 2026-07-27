"""原料报告单 API"""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.core.database import AsyncSession, get_db  # type: ignore[attr-defined]
from app.core.exceptions import AppException, NotFoundException
from app.core.response import ApiResponse
from app.core.storage import save_upload_file
from app.modules.quality.qms.material_report_schemas import (
    ReportCreate,
    ReportItemsBatchSave,
    ReportUpdate,
    TemplateCreate,
    TemplateUpdate,
)
from app.modules.quality.qms.material_report_service import (
    MaterialReportService,
    ReportTemplateService,
)

router = APIRouter(prefix="/quality/material-report", tags=["原料报告单"])


# ============ 报告单 API ============


@router.get("/", summary="获取报告单列表")
async def get(
    template_id: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    keyword: str | None = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
) -> Any:
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
async def post(
    data: ReportCreate,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """创建报告单"""
    service = MaterialReportService(session)
    report = await service.create_report(data)
    return ApiResponse(data={"id": str(report.id), "report_no": report.report_no})  # type: ignore[attr-defined]


@router.get("/statistics", summary="获取统计数据")  # type: ignore[no-redef]
async def get(  # noqa: F811
    session: AsyncSession = Depends(get_db),
) -> Any:
    """获取统计数据"""
    service = MaterialReportService(session)
    stats = await service.get_statistics()
    return ApiResponse(data=stats)


@router.get("/template", summary="获取模板列表")  # type: ignore[no-redef]
async def get(  # noqa: F811
    is_active: bool | None = None,
    page: int = 1,
    page_size: int = 20,
    session: AsyncSession = Depends(get_db),
) -> Any:
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


@router.post("/template/", summary="上传Word模板")  # type: ignore[no-redef]
async def post(  # noqa: F811
    file: UploadFile = File(..., description="Word模板文件"),
    template_name: str = Form(..., description="模板名称"),
    template_description: str | None = Form(None, description="模板描述"),
    field_mapping: str | None = Form(None, description="静态字段映射JSON"),
    table_fields: str | None = Form(None, description="动态表格字段JSON"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """上传Word模板"""
    # 验证文件类型
    if not file.filename.endswith((".docx", ".doc")):  # type: ignore[union-attr]
        raise AppException(status_code=400, message="仅支持Word文档(.docx, .doc)")

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


@router.get("/template/{template_id}", summary="获取模板详情")  # type: ignore[no-redef]
async def get(  # noqa: F811
    template_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """获取模板详情"""
    service = ReportTemplateService(session)
    template = await service.get_template(template_id)

    if not template:
        raise NotFoundException(resource="模板不存在")

    return ApiResponse(data=template)


@router.put("/template/{template_id}", summary="更新模板")  # type: ignore[no-redef]
async def put(  # noqa: F811
    template_id: UUID,
    data: TemplateUpdate,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """更新模板"""
    service = ReportTemplateService(session)
    template = await service.update_template(template_id, data)

    if not template:
        raise NotFoundException(resource="模板不存在")

    return ApiResponse(data=template)


@router.delete("/template/{template_id}", summary="删除模板")  # type: ignore[no-redef]
async def delete(  # noqa: F811
    template_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """删除模板"""
    service = ReportTemplateService(session)
    success = await service.delete_template(template_id)

    if not success:
        raise NotFoundException(resource="模板不存在")

    return ApiResponse(message="删除成功")


@router.get("/template/{template_id}/preview", summary="预览模板字段")  # type: ignore[no-redef]
async def get(  # noqa: F811
    template_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """解析模板获取字段配置"""
    service = ReportTemplateService(session)
    result = await service.parse_template(template_id)

    if not result:
        raise NotFoundException(resource="模板不存在")

    return ApiResponse(data=result)


# ============ 图片上传与AI识别 API ============


@router.get("/{report_id}", summary="获取报告单详情")  # type: ignore[no-redef]
async def get(  # noqa: F811
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """获取报告单详情"""
    service = MaterialReportService(session)
    report = await service.get_report(report_id)

    if not report:
        raise NotFoundException(resource="报告单不存在")

    return ApiResponse(data=report)


@router.put("/{report_id}", summary="更新报告单")  # type: ignore[no-redef]
async def put(  # noqa: F811
    report_id: UUID,
    data: ReportUpdate,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """更新报告单"""
    service = MaterialReportService(session)
    report = await service.update_report(report_id, data)

    if not report:
        raise NotFoundException(resource="报告单不存在")

    return ApiResponse(data=report)


@router.delete("/{report_id}", summary="删除报告单")  # type: ignore[no-redef]
async def delete(  # noqa: F811
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """删除报告单"""
    service = MaterialReportService(session)
    success = await service.delete_report(report_id)

    if not success:
        raise NotFoundException(resource="报告单不存在")

    return ApiResponse(message="删除成功")


@router.post("/{report_id}/items", summary="批量保存明细数据")  # type: ignore[no-redef]
async def post(  # noqa: F811
    report_id: UUID,
    data: ReportItemsBatchSave,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """批量保存明细数据"""
    service = MaterialReportService(session)

    # 检查报告单是否存在
    report = await service.get_report(report_id)
    if not report:
        raise NotFoundException(resource="报告单不存在")

    items = await service.save_items(report_id, data)
    return ApiResponse(data={"items": items})


@router.post("/{report_id}/generate", summary="生成报告单文件")  # type: ignore[no-redef]
async def post(  # noqa: F811
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """生成报告单Word文件并下载"""
    service = MaterialReportService(session)

    try:
        content = await service.generate_report(report_id)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))

    # 获取报告单信息用于文件名
    report = await service.get_report(report_id)
    filename = f"{report['report_no']}.docx"

    return StreamingResponse(
        iter([content]),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{filename}"},
    )


@router.post("/{report_id}/submit", summary="提交报告单")  # type: ignore[no-redef]
async def post(  # noqa: F811
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """提交报告单"""
    service = MaterialReportService(session)

    try:
        report = await service.submit_report(report_id)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))

    return ApiResponse(data=report)


# ============ 模板管理 API ============


@router.post("/{report_id}/images", summary="上传图片并AI识别")  # type: ignore[no-redef]
async def post(  # noqa: F811
    report_id: UUID,
    field_key: str | None = Form(None, description="对应字段key"),
    row_index: int | None = Form(None, description="对应行序号"),
    file: UploadFile = File(..., description="图片文件"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """上传图片并进行AI识别"""
    service = MaterialReportService(session)

    # 检查报告单是否存在
    report = await service.get_report(report_id)
    if not report:
        raise NotFoundException(resource="报告单不存在")

    try:
        result = await service.upload_image_and_recognize(
            report_id=report_id,
            field_key=field_key,
            row_index=row_index,
            file=file,
        )
        return ApiResponse(data=result)
    except ValueError as e:
        raise AppException(status_code=400, message=str(e))


@router.get("/{report_id}/images", summary="获取报告单图片列表")  # type: ignore[no-redef]
async def get(  # noqa: F811
    report_id: UUID,
    session: AsyncSession = Depends(get_db),
) -> Any:
    """获取报告单的所有图片记录"""
    service = MaterialReportService(session)
    images = await service.get_report_images(report_id)
    return ApiResponse(data=images)
