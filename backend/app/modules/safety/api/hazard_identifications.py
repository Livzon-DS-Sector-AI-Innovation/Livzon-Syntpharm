# mypy: ignore-errors
"""Safety API — hazard_identifications endpoints."""

import os
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ApiResponse  # type: ignore[attr-defined]
from app.core.storage import is_enabled as minio_enabled
from app.core.storage import upload_object
from app.modules.safety.schemas import (
    HazardIdentificationBatchCreate,
    HazardIdentificationCreate,
    HazardIdentificationResponse,
    HazardIdentificationReview,
    HazardIdentificationRunScript,
    HazardIdentificationUpdate,
    HazardLedgerExportRequest,
    HazardRiskOption,
)
from app.modules.safety.service import (
    DailyRiskReportService,
    SafetyService,
)

hazard_identifications_router = APIRouter()


@hazard_identifications_router.get(
    "/hazard-identifications",
    response_model=ApiResponse,
    summary="获取危险源辨识列表",
)
async def handler(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    department: str | None = None,
    overall_status: str | None = None,
    ai_node_progress: str | None = None,
    keyword: str | None = None,
    position: str | None = None,
    risk_level: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    batch_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取危险源辨识列表"""
    service = SafetyService(db)
    skip = (page - 1) * page_size
    items, total = await service.get_hazard_identifications(
        skip,
        page_size,
        department,
        overall_status,
        ai_node_progress,
        keyword,
        position,
        risk_level,
        date_from,
        date_to,
        batch_id,
    )
    return ApiResponse(
        data=[HazardIdentificationResponse.model_validate(i) for i in items],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@hazard_identifications_router.get(  # type: ignore[no-redef]
    "/hazard-identifications/stats",
    response_model=ApiResponse,
    summary="获取危险源辨识工作流统计",
)
async def handler(  # noqa: F811
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取危险源辨识工作流统计（草案/进行中/待审核/已完成）"""
    service = SafetyService(db)
    stats = await service.get_hazard_identification_stats()
    return ApiResponse(data=stats)


@hazard_identifications_router.get(  # type: ignore[no-redef]
    "/hazard-identifications/ledger-stats",
    response_model=ApiResponse,
    summary="获取危险源辨识台账统计",
)
async def handler(  # noqa: F811
    department: str | None = Query(None),
    position: str | None = Query(None),
    risk_level: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取危险源辨识台账统计（总记录/按风险等级分组）"""
    service = SafetyService(db)
    stats = await service.get_hazard_identification_ledger_stats(
        department,
        position,
        risk_level,
        date_from,
        date_to,
    )
    return ApiResponse(data=stats)


@hazard_identifications_router.get(  # type: ignore[no-redef]
    "/hazard-identifications/risk-options",
    response_model=ApiResponse,
    summary="获取危险源风险选项（常规作业报备用）",
)
async def handler(  # noqa: F811
    department: str | None = Query(None, description="部门筛选"),
    keyword: str | None = Query(None, description="搜索关键字（编号/部门/岗位）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """返回风险等级为 level_1/level_2 且 overall_status=completed 的危险源辨识项"""
    service = SafetyService(db)
    skip = (page - 1) * page_size
    items, total = await service.get_hazard_risk_options(department, keyword, skip, page_size)
    return ApiResponse(
        data=[HazardRiskOption.model_validate(i) for i in items],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@hazard_identifications_router.get(  # type: ignore[no-redef]
    "/hazard-identifications/{hid}",
    response_model=ApiResponse,
    summary="获取危险源辨识详情",
)
async def handler(  # noqa: F811
    hid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """获取危险源辨识详情"""
    service = SafetyService(db)
    item = await service.get_hazard_identification(hid)
    if not item:
        return ApiResponse(code=404, message="记录不存在")
    return ApiResponse(data=HazardIdentificationResponse.model_validate(item))


@hazard_identifications_router.post(  # type: ignore[no-redef]
    "/hazard-identifications",
    response_model=ApiResponse,
    summary="创建危险源辨识记录",
)
async def handler(  # noqa: F811
    data: HazardIdentificationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """创建危险源辨识记录（填写基础信息）"""
    service = SafetyService(db)
    item = await service.create_hazard_identification(data)
    await db.commit()
    return ApiResponse(data=HazardIdentificationResponse.model_validate(item))


# ── 批量辨识 + 工段预览 ──


@hazard_identifications_router.get(  # type: ignore[no-redef]
    "/regulations/{regulation_id}/stages",
    response_model=ApiResponse,
    summary="获取操规工艺阶段列表（批量辨识前预览）",
)
async def handler(  # noqa: F811
    regulation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """解析操规 Chapter 7 → 返回工艺阶段名称 + 安全要求/操作步骤数量"""
    service = SafetyService(db)
    stages = await service.get_regulation_stages(regulation_id)
    if stages is None:
        return ApiResponse(code=404, message="操规不存在或无可解析的第七章内容")
    return ApiResponse(data=stages)


@hazard_identifications_router.post(  # type: ignore[no-redef]
    "/hazard-identifications/batch",
    response_model=ApiResponse,
    summary="批量创建危险源辨识（一个操规多工段）",
)
async def handler(  # noqa: F811
    data: HazardIdentificationBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """根据操规第7章的工艺阶段，批量创建危险源辨识记录"""
    service = SafetyService(db)
    try:
        result = await service.create_hazard_identification_batch(data)
        await db.commit()
        return ApiResponse(data=result)
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@hazard_identifications_router.put(  # type: ignore[no-redef]
    "/hazard-identifications/{hid}",
    response_model=ApiResponse,
    summary="更新危险源辨识记录",
)
async def handler(  # noqa: F811
    hid: uuid.UUID,
    data: HazardIdentificationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """更新危险源辨识记录（人工编辑字段）"""
    service = SafetyService(db)
    item = await service.update_hazard_identification(hid, data)
    if not item:
        return ApiResponse(code=404, message="记录不存在")
    await db.commit()
    return ApiResponse(data=HazardIdentificationResponse.model_validate(item))


@hazard_identifications_router.post(  # type: ignore[no-redef]
    "/hazard-identifications/{hid}/submit",
    response_model=ApiResponse,
    summary="提交基础信息，进入AI流程",
)
async def handler(  # noqa: F811
    hid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """提交基础信息 → 进入待AI解析附件阶段"""
    service = SafetyService(db)
    item = await service.submit_hazard_identification(hid)
    if not item:
        return ApiResponse(code=400, message="无法提交，当前状态不允许")
    await db.commit()
    return ApiResponse(data=HazardIdentificationResponse.model_validate(item))


@hazard_identifications_router.post(  # type: ignore[no-redef]
    "/hazard-identifications/{hid}/run-script",
    response_model=ApiResponse,
    summary="执行AI脚本",
)
async def handler(  # noqa: F811
    hid: uuid.UUID,
    data: HazardIdentificationRunScript,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """执行指定编号的AI脚本（脚本1-7）"""
    service = SafetyService(db)
    item = await service.run_script(hid, data.script_number, data.ai_output)
    if not item:
        return ApiResponse(code=400, message="无法执行脚本，当前状态不允许或条件不满足")
    await db.commit()
    return ApiResponse(data=HazardIdentificationResponse.model_validate(item))


@hazard_identifications_router.post(  # type: ignore[no-redef]
    "/hazard-identifications/{hid}/review",
    response_model=ApiResponse,
    summary="审核脚本输出",
)
async def handler(  # noqa: F811
    hid: uuid.UUID,
    data: HazardIdentificationReview,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """审核确认或驳回AI脚本输出结果"""
    service = SafetyService(db)
    item = await service.review_script(hid, data.script_number, data.action)
    if not item:
        return ApiResponse(code=400, message="无法审核，当前状态不允许")
    await db.commit()
    return ApiResponse(data=HazardIdentificationResponse.model_validate(item))


@hazard_identifications_router.post(  # type: ignore[no-redef]
    "/hazard-identifications/{hid}/upload",
    response_model=ApiResponse,
    summary="上传岗位资料附件",
)
async def handler(  # noqa: F811
    hid: uuid.UUID,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """上传危险源辨识的岗位资料附件"""

    file_ext = os.path.splitext(file.filename or ".bin")[1]
    safe_name = f"{hid}_{int(datetime.now().timestamp())}{file_ext}"
    content = await file.read()

    if minio_enabled():
        object_key = f"hazard-identification/{safe_name}"
        upload_object(
            "safety",
            object_key,
            content,
            len(content),
            file.content_type or "application/octet-stream",
        )
        stored_path = object_key
    else:
        upload_dir = os.path.join("uploads", "safety", "hazard")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, safe_name)
        with open(file_path, "wb") as f:
            f.write(content)
        stored_path = file_path

    service = SafetyService(db)
    item = await service.upload_attachment(hid, file.filename or "unknown", stored_path)
    if not item:
        return ApiResponse(code=404, message="记录不存在")
    await db.commit()
    return ApiResponse(data=HazardIdentificationResponse.model_validate(item))


@hazard_identifications_router.delete(  # type: ignore[no-redef]
    "/hazard-identifications/{hid}",
    response_model=ApiResponse,
    summary="删除危险源辨识记录",
)
async def handler(  # noqa: F811
    hid: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """删除危险源辨识记录"""
    service = SafetyService(db)
    result = await service.delete_hazard_identification(hid)
    if not result:
        return ApiResponse(code=404, message="记录不存在")
    await db.commit()
    return ApiResponse(message="删除成功")


# ── 危险源辨识台账导出 ──


@hazard_identifications_router.post(  # type: ignore[no-redef]
    "/hazard-identifications/parse-query",
    response_model=ApiResponse,
    summary="AI 解析危险源辨识台账自然语言筛选条件",
)
async def handler(  # noqa: F811
    data: HazardLedgerExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """使用 AI 将自然语言查询解析为结构化的危险源辨识台账筛选条件"""
    service = SafetyService(db)
    if not data.natural_query:
        return ApiResponse(code=400, message="请提供自然语言查询")
    result = await service.parse_hazard_export_query(data.natural_query)
    return ApiResponse(data=result)


@hazard_identifications_router.post(  # type: ignore[no-redef]
    "/hazard-identifications/export-pdf",
    summary="导出危险源辨识台账 PDF",
)
async def handler(  # noqa: F811
    data: HazardLedgerExportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """导出危险源辨识台账为 PDF 文件。

    流程：
    1. AI 解析自然语言 → 筛选条件（如「导出所有重大危险源」「提炼一部上月记录」）
    2. 按条件查询数据库
    3. Excel 标准化输出插件填表 → LibreOffice 转 PDF

    不提供 natural_query 时导出全部已完成记录。
    """
    from datetime import datetime as dt_module
    from urllib.parse import quote

    from fastapi.responses import Response

    service = SafetyService(db)

    pdf_bytes = await service.export_hazard_ledger_pdf(
        natural_query=data.natural_query,
        department=data.department,
        position=data.position,
        risk_level=data.risk_level,
        date_from=data.date_from,
        date_to=data.date_to,
        keyword=data.keyword,
    )

    filename = f"危险源辨识台账_{dt_module.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    ascii_filename = f"hazard_ledger_{dt_module.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{quote(filename)}"),
            "Content-Length": str(len(pdf_bytes)),
        },
    )
