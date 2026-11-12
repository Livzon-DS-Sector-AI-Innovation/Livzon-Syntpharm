"""偏差台账 API：列表 / 统计 / 详情 / 新建 / 编辑 / 流转 / 报告 / 附件 / 批量与删除。

路由注册顺序要求：静态路径（``/statistics``、``/department-options`` 等）必须写在
``/{ledger_id}`` 之前，否则会被动态段吞掉。
"""

from __future__ import annotations

from datetime import date
from io import BytesIO
from urllib.parse import quote
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import ApiResponse, build_response

from .deviation_ledger_schemas import (
    AttachmentListApiResponse,
    AttachmentListData,
    BatchResultApiResponse,
    BatchResultData,
    BatchStatusRequest,
    CompleteAiAnalysisRequest,
    CrossDeptApproveRequest,
    DeleteResultApiResponse,
    DeleteResultData,
    FinalCodeRequest,
    InvestigationRequest,
    LedgerCreateRequest,
    LedgerDetailApiResponse,
    LedgerListApiResponse,
    LedgerListData,
    LedgerOptionsApiResponse,
    LedgerStatisticsApiResponse,
    LedgerUpdateRequest,
    OptionListData,
    ReportSaveRequest,
    ResubmitRequest,
    ReviewRequest,
    status_options,
)
from .deviation_ledger_service import DeviationLedgerService

router = APIRouter(prefix="/deviation/ledger", tags=["质量管理 - 偏差台账"])

_READ = "quality:deviation:read"
_CREATE = "quality:deviation:create"
_UPDATE = "quality:deviation:update"
_SUBMIT = "quality:deviation:submit"
_APPROVE = "quality:deviation:approve"
_DELETE = "quality:deviation:delete"


def _is_superuser(ctx: PermissionContext) -> bool:
    return bool(getattr(ctx, "is_superuser", False))


@router.get("", response_model=LedgerListApiResponse, summary="偏差台账列表")
async def list_ledger(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
    status: str | None = Query(None, description="状态"),
    department: str | None = Query(None, description="发生部门"),
    reason_category: str | None = Query(None, description="原因分类"),
    start_date: date | None = Query(None, description="发现日期起"),
    end_date: date | None = Query(None, description="发现日期止"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
) -> ApiResponse:
    """按原因分类 / 状态 / 发生部门筛选，按发现日期倒序。"""
    service = DeviationLedgerService(db)
    items, total = await service.list_items(
        status=status,
        department=department,
        reason_category=reason_category,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return build_response(
        data=LedgerListData(items=items, total=total, page=page, page_size=page_size),
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/statistics", response_model=LedgerStatisticsApiResponse, summary="偏差看盘统计")
async def ledger_statistics(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """统计卡 + 部门分布 + 状态分布 + 环节分布（不含 CAPA 看盘）。"""
    service = DeviationLedgerService(db)
    return build_response(data=await service.statistics())


@router.get("/department-options", response_model=LedgerOptionsApiResponse, summary="发生部门候选")
async def ledger_department_options(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """筛选栏部门下拉（覆盖台账已有部门，含未配置联系人的历史部门）。"""
    service = DeviationLedgerService(db)
    return build_response(data=OptionListData(items=await service.department_options()))


@router.get(
    "/department-contact-options",
    response_model=LedgerOptionsApiResponse,
    summary="新建/编辑可用部门（部门联系人配置）",
)
async def ledger_department_contact_options(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """新建与编辑表单的部门下拉：只列已配置联系人的部门，保证节点负责人可解析。"""
    service = DeviationLedgerService(db)
    return build_response(data=OptionListData(items=await service.contact_department_options()))


@router.get("/investigator-options", response_model=LedgerOptionsApiResponse, summary="调查人候选")
async def ledger_investigator_options(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
    keyword: str | None = Query(None, description="姓名关键字"),
) -> ApiResponse:
    """新建与编辑表单的调查人选择器候选。"""
    service = DeviationLedgerService(db)
    return build_response(data=OptionListData(items=await service.investigator_options(keyword)))


@router.get("/status-options", response_model=LedgerOptionsApiResponse, summary="状态候选")
async def ledger_status_options(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
) -> ApiResponse:
    """筛选栏与批量操作的状态下拉，避免前端硬编码 12 态。"""
    return build_response(data=OptionListData(items=status_options()))


@router.patch("/batch-status", response_model=BatchResultApiResponse, summary="批量更新状态")
async def batch_update_status(
    payload: BatchStatusRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """勾选多行批量改状态（管理动作，需二次确认）。"""
    service = DeviationLedgerService(db)
    updated = await service.batch_update_status(payload, actor_id=current_user.id)
    return build_response(data=BatchResultData(updated=updated), message=f"已更新 {updated} 条")


@router.get("/{ledger_id}", response_model=LedgerDetailApiResponse, summary="偏差详情")
async def get_ledger(
    ledger_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """整页详情：主表 + AI 分析 + 调查报告 + 调查记录 + 审核全过程 + 附件 + 步骤条。"""
    service = DeviationLedgerService(db)
    detail = await service.get_detail(
        ledger_id,
        viewer_id=current_user.id,
        viewer_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail)


@router.post("", response_model=LedgerDetailApiResponse, summary="新建偏差")
async def create_ledger(
    payload: LedgerCreateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_CREATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """新建偏差：发现人 / 上报人取当前登录人，初始状态为待 AI 分析。"""
    service = DeviationLedgerService(db)
    detail = await service.create(payload, user_id=current_user.id)
    return build_response(data=detail, message="偏差创建成功")


@router.put("/{ledger_id}", response_model=LedgerDetailApiResponse, summary="修改基础信息")
async def update_ledger(
    ledger_id: UUID,
    payload: LedgerUpdateRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """仅在待 AI 分析 / 已退回状态可修改，含调查人与跨部门配置。"""
    service = DeviationLedgerService(db)
    detail = await service.update(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="保存成功")


@router.delete("/{ledger_id}", response_model=DeleteResultApiResponse, summary="删除偏差")
async def delete_ledger(
    ledger_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_DELETE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """软删除：任意状态均可删除，仅标记删除位，数据仍可追溯。"""
    service = DeviationLedgerService(db)
    await service.delete(ledger_id, actor_id=current_user.id)
    return build_response(data=DeleteResultData(id=ledger_id), message="删除成功")


@router.post("/{ledger_id}/ai-analysis", response_model=LedgerDetailApiResponse, summary="生成 AI 分析")
async def generate_ai_analysis(
    ledger_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """调用大模型生成结构化分析（只返回，不落库）。"""
    service = DeviationLedgerService(db)
    analysis = await service.generate_ai_analysis(ledger_id)
    detail = await service.get_detail(ledger_id, viewer_id=current_user.id)
    detail.ai_analysis = analysis
    return build_response(data=detail, message="AI 分析已生成")


@router.post(
    "/{ledger_id}/complete-ai-analysis",
    response_model=LedgerDetailApiResponse,
    summary="保存 AI 分析结果",
)
async def complete_ai_analysis(
    ledger_id: UUID,
    payload: CompleteAiAnalysisRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """保存分析结果：只写库、不推进流程，流程由「提交调查报告」驱动。"""
    service = DeviationLedgerService(db)
    detail = await service.save_ai_analysis(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="分析结果已保存")


@router.post("/{ledger_id}/investigation", response_model=LedgerDetailApiResponse, summary="提交调查")
async def submit_investigation(
    ledger_id: UUID,
    payload: InvestigationRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_SUBMIT)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """追加一条调查记录并提交部门负责人审核。"""
    service = DeviationLedgerService(db)
    detail = await service.submit_investigation(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="调查已提交")


@router.post(
    "/{ledger_id}/investigation-records",
    response_model=LedgerDetailApiResponse,
    summary="追加调查记录（不流转）",
)
async def append_investigation_record(
    ledger_id: UUID,
    payload: InvestigationRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_SUBMIT)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """审核阶段补充调查：只追加调查记录，不改变流程状态。"""
    service = DeviationLedgerService(db)
    detail = await service.append_investigation_record(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="调查记录已追加")


@router.post("/{ledger_id}/review", response_model=LedgerDetailApiResponse, summary="审核通过 / 退回")
async def review_ledger(
    ledger_id: UUID,
    payload: ReviewRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """按当前环节审核：通过推进下一环节，退回回到本环节并通知上报人。"""
    service = DeviationLedgerService(db)
    detail = await service.review(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    message = "已通过" if payload.result == "approved" else "已退回"
    return build_response(data=detail, message=message)


@router.post(
    "/{ledger_id}/cross-dept-review",
    response_model=LedgerDetailApiResponse,
    summary="跨部门逐行审批通过",
)
async def approve_cross_dept_row(
    ledger_id: UUID,
    payload: CrossDeptApproveRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_APPROVE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """该行审核人通过后仅完成该部门节点；全部跨部门行通过后进入所属 QA 审核。"""
    service = DeviationLedgerService(db)
    detail = await service.approve_cross_dept(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    advanced = detail.current_step != "cross_dept_head_review"
    return build_response(data=detail, message="该部门已审核通过" + ("，跨部门审核全部完成" if advanced else ""))


@router.post("/{ledger_id}/resubmit", response_model=LedgerDetailApiResponse, summary="退回后重新提交")
async def resubmit_ledger(
    ledger_id: UUID,
    payload: ResubmitRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_SUBMIT)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """回到被退回的环节，审核人不变。"""
    service = DeviationLedgerService(db)
    detail = await service.resubmit(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="已重新提交")


@router.post("/{ledger_id}/final-code", response_model=LedgerDetailApiResponse, summary="输入最终编号")
async def submit_final_code(
    ledger_id: UUID,
    payload: FinalCodeRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """录入最终编号，偏差关闭。"""
    service = DeviationLedgerService(db)
    detail = await service.submit_final_code(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="偏差已关闭")


@router.put("/{ledger_id}/report", response_model=LedgerDetailApiResponse, summary="保存调查报告")
async def save_report(
    ledger_id: UUID,
    payload: ReportSaveRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """保存报告正文并按需追加版本记录。"""
    service = DeviationLedgerService(db)
    detail = await service.save_report(
        ledger_id,
        payload,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="报告已保存")


@router.post("/{ledger_id}/attachments", response_model=LedgerDetailApiResponse, summary="上传附件")
async def upload_attachment(
    ledger_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
    file: UploadFile = File(..., description="附件文件"),
) -> ApiResponse:
    """单个附件上限 20MB，二进制进对象存储，DB 只存元数据。"""
    service = DeviationLedgerService(db)
    detail = await service.add_attachment(
        ledger_id,
        file,
        actor_id=current_user.id,
        actor_name=current_user.name or "-",
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="附件已上传")


@router.delete(
    "/{ledger_id}/attachments/{file_id}",
    response_model=LedgerDetailApiResponse,
    summary="删除附件",
)
async def delete_attachment(
    ledger_id: UUID,
    file_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_UPDATE)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """删除附件元数据并清理对象存储。"""
    service = DeviationLedgerService(db)
    detail = await service.remove_attachment(
        ledger_id,
        file_id,
        actor_id=current_user.id,
        actor_is_superuser=_is_superuser(ctx),
    )
    return build_response(data=detail, message="附件已删除")


@router.get(
    "/{ledger_id}/attachments/{file_id}/download",
    summary="下载附件",
    response_model=None,
)
async def download_attachment(
    ledger_id: UUID,
    file_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """下载前校验附件归属该偏差；中文文件名按 RFC 5987 编码。"""
    service = DeviationLedgerService(db)
    file_name, content, content_type = await service.get_attachment_file(ledger_id, file_id)
    return StreamingResponse(
        BytesIO(content),
        media_type=content_type or "application/octet-stream",
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(file_name)}",
            "Content-Length": str(len(content)),
        },
    )


@router.get(
    "/{ledger_id}/attachments",
    response_model=AttachmentListApiResponse,
    summary="附件列表",
)
async def list_attachments(
    ledger_id: UUID,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission(_READ)),
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """详情页附件卡片使用（详情接口已内联，此端点供局部刷新）。"""
    service = DeviationLedgerService(db)
    detail = await service.get_detail(ledger_id, viewer_id=current_user.id)
    return build_response(data=AttachmentListData(items=detail.attachments))
