"""Doc Check 模块 API 路由

提供文档合规校验的 RESTful API 接口。
前缀: /api/v1/doc-check/
"""

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, get_current_user
from app.core.response import ApiResponse
from app.modules.quality.qms.doc_check.schemas import (
    DocCheckConfigCreate,
    DocCheckConfigResponse,
    DocCheckConfigUpdate,
    DocCheckCreate,
    DocCheckDetailResponse,
    DocCheckResponse,
    DocCheckUpdate,
    ProblemResponse,
    ProblemUpdate,
)
from app.modules.quality.qms.doc_check.service import DocCheckService

router = APIRouter()


# 模拟上传存储（生产环境应使用对象存储）
_upload_store: dict[str, dict[str, Any]] = {}


# ============ 配置接口 ============


@router.get("/config", response_model=ApiResponse, summary="获取配置列表")
async def get_configs(
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取配置列表"""
    try:
        service = DocCheckService(db)
        configs = await service.get_configs()
        return ApiResponse(
            data=[DocCheckConfigResponse.model_validate(c) for c in configs]
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return ApiResponse(code=500, message=f"Error: {type(e).__name__}: {str(e)}")


@router.get("/config/{config_id}", response_model=ApiResponse, summary="获取配置详情")
async def get_config(
    config_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取配置详情"""
    service = DocCheckService(db)
    config = await service.get_config_by_key(str(config_id))
    if not config:
        return ApiResponse(code=404, message="配置不存在")
    return ApiResponse(data=DocCheckConfigResponse.model_validate(config))


@router.post("/config", response_model=ApiResponse, summary="创建配置")
async def create_config(
    data: DocCheckConfigCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建配置"""
    service = DocCheckService(db)
    config = await service.create_config(data)
    await db.commit()
    return ApiResponse(data=DocCheckConfigResponse.model_validate(config))


@router.put("/config/{config_id}", response_model=ApiResponse, summary="更新配置")
async def update_config(
    config_id: uuid.UUID,
    data: DocCheckConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新配置"""
    service = DocCheckService(db)
    config = await service.update_config(config_id, data)
    if not config:
        return ApiResponse(code=404, message="配置不存在")
    await db.commit()
    return ApiResponse(data=DocCheckConfigResponse.model_validate(config))


# ============ 校验接口 ============


@router.post("/check", response_model=ApiResponse, summary="创建校验任务")
async def create_check(
    data: DocCheckCreate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """创建校验任务"""
    try:
        service = DocCheckService(db)
        operator = current_user.username if current_user else None
        check = await service.create_check(data, operator=operator)
        await db.commit()
        # 返回前端需要的格式
        return ApiResponse(
            data={
                "task_id": str(check.id),
                "check_no": check.file_code,
                "file_name": check.file_name,
                "status": check.status.value
                if hasattr(check.status, "value")
                else check.status,
            }
        )
    except Exception as e:
        import traceback

        traceback.print_exc()
        return ApiResponse(code=500, message=f"{type(e).__name__}: {str(e)}")


@router.post(
    "/check/{check_id}/execute", response_model=ApiResponse, summary="执行校验"
)
async def execute_check(
    check_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """执行校验（调用 AI）"""
    service = DocCheckService(db)
    operator = current_user.username if current_user else None
    try:
        check = await service.execute_check(check_id, operator=operator)
        if not check:
            return ApiResponse(code=404, message="校验任务不存在")
        await db.commit()
        return ApiResponse(data=DocCheckDetailResponse.model_validate(check))
    except Exception as e:
        return ApiResponse(code=500, message=str(e))


@router.get("/check", response_model=ApiResponse, summary="获取校验列表")
async def get_checks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    status: str | None = Query(None, description="校验状态"),
    doc_type: str | None = Query(None, description="文档类型"),
    operator: str | None = Query(None, description="操作人"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取校验列表"""
    service = DocCheckService(db)
    skip = (page - 1) * page_size
    checks, total = await service.get_checks(
        skip=skip,
        limit=page_size,
        status=status,
        doc_type=doc_type,
        operator=operator,
    )
    return ApiResponse(
        data=[DocCheckResponse.model_validate(c) for c in checks],
        meta={"page": page, "page_size": page_size, "total": total},
    )


@router.get("/check/{check_id}", response_model=ApiResponse, summary="获取校验详情")
async def get_check(
    check_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取校验详情"""
    service = DocCheckService(db)
    check = await service.get_check(check_id)
    if not check:
        return ApiResponse(code=404, message="校验任务不存在")
    return ApiResponse(data=DocCheckDetailResponse.model_validate(check))


@router.put("/check/{check_id}", response_model=ApiResponse, summary="更新校验任务")
async def update_check(
    check_id: uuid.UUID,
    data: DocCheckUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新校验任务"""
    service = DocCheckService(db)
    try:
        check = await service.update_check(check_id, data)
        if not check:
            return ApiResponse(code=404, message="校验任务不存在")
        await db.commit()
        return ApiResponse(data=DocCheckResponse.model_validate(check))
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


@router.delete("/check/{check_id}", response_model=ApiResponse, summary="删除校验任务")
async def delete_check(
    check_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """删除校验任务"""
    service = DocCheckService(db)
    try:
        result = await service.delete_check(check_id)
        if not result:
            return ApiResponse(code=404, message="校验任务不存在")
        await db.commit()
        return ApiResponse(message="删除成功")
    except ValueError as e:
        return ApiResponse(code=400, message=str(e))


# ============ 问题接口 ============


@router.get("/problems", response_model=ApiResponse, summary="获取问题列表")
async def get_problems(
    check_main_id: uuid.UUID = Query(..., description="校验主表ID"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取问题列表"""
    service = DocCheckService(db)
    problems = await service.get_problems(check_main_id)
    return ApiResponse(data=[ProblemResponse.model_validate(p) for p in problems])


# ============ 向量缓存接口 ============


@router.get("/vector-cache", response_model=ApiResponse, summary="获取向量缓存列表")
async def get_vector_cache(
    doc_type: str | None = Query(None, description="文档类型"),
    doc_hash: str | None = Query(None, description="文档哈希"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取向量缓存列表"""
    service = DocCheckService(db)
    caches = await service.get_vector_cache(doc_type=doc_type, doc_hash=doc_hash)
    return ApiResponse(data=caches)


# ============ 文件上传接口 ============


@router.post("/upload", response_model=ApiResponse, summary="上传文件")
async def upload_file(
    file: UploadFile = File(...),
    file_name: str = Form(..., description="文件名"),
    file_no: str | None = Form(None, description="文件编号"),
    file_version: str | None = Form(None, description="文件版本"),
    file_type: str | None = Form(None, description="文件类型"),
    preparer: str | None = Form(None, description="编制人"),
    prepare_date: str | None = Form(None, description="编制日期"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """上传文件到服务器"""
    # 读取文件内容
    content = await file.read()
    file_size = len(content)

    # 生成文件ID
    file_id = str(uuid.uuid4())

    # 保存到存储（生产环境应使用对象存储）
    # Word文档使用docx库读取文本内容
    content_text = ""
    if (
        file.content_type
        == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ):
        try:
            from io import BytesIO

            from docx import Document

            doc = Document(BytesIO(content))
            content_text = "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            logger.warning(f"Failed to extract text from docx: {e}")
            content_text = ""
    elif file.content_type == "text/plain":
        try:
            content_text = content.decode("utf-8")
        except Exception:
            content_text = ""

    _upload_store[file_id] = {
        "file_id": file_id,
        "file_name": file_name,
        "file_no": file_no,
        "file_version": file_version,
        "file_type": file_type,
        "preparer": preparer,
        "prepare_date": prepare_date,
        "file_size": file_size,
        "file_ext": file.filename.split(".")[-1] if "." in file.filename else "",
        "content": content_text,
        "status": "uploaded",
    }

    return ApiResponse(
        data={
            "file_id": file_id,
            "file_name": file_name,
            "file_path": f"/uploads/{file_id}",
            "file_size": file_size,
            "file_ext": file.filename.split(".")[-1] if "." in file.filename else "",
        }
    )


@router.get(
    "/upload/{upload_id}/progress", response_model=ApiResponse, summary="获取上传进度"
)
async def get_upload_progress(
    upload_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取上传进度"""
    if upload_id not in _upload_store:
        return ApiResponse(code=404, message="上传记录不存在")

    upload_data = _upload_store[upload_id]
    progress = 100 if upload_data.get("status") == "uploaded" else 0

    return ApiResponse(
        data={
            "progress": progress,
            "file_id": upload_id if progress == 100 else None,
        }
    )


# ============ 校验进度接口 ============


@router.get(
    "/check/{check_id}/progress", response_model=ApiResponse, summary="获取校验进度"
)
async def get_check_progress(
    check_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取校验进度"""
    service = DocCheckService(db)
    check = await service.get_check(check_id)

    if not check:
        return ApiResponse(code=404, message="校验任务不存在")

    # 计算进度
    status_map = {
        "pending": 0,
        "running": 50,
        "completed": 100,
        "failed": 100,
        "cancelled": 100,
    }
    progress = status_map.get(check.status, 0)

    # 步骤映射
    step_map = {
        "pending": "等待处理",
        "running": "AI校验中",
        "completed": "校验完成",
        "failed": "校验失败",
        "cancelled": "已取消",
    }

    return ApiResponse(
        data={
            "task_id": str(check.id),
            "status": check.status,
            "progress": progress,
            "current_step": step_map.get(check.status, "未知"),
            "message": check.check_result if check.check_result else None,
        }
    )


@router.post("/check/{check_id}/cancel", response_model=ApiResponse, summary="取消校验")
async def cancel_check(
    check_id: uuid.UUID,
    operator: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """取消校验任务"""
    service = DocCheckService(db)
    operator = operator or (current_user.username if current_user else None)

    check = await service.get_check(check_id)
    if not check:
        return ApiResponse(code=404, message="校验任务不存在")

    if check.status not in ["pending", "running"]:
        return ApiResponse(code=400, message="只有待处理或处理中的任务才能取消")

    await service.update_check(check_id, DocCheckUpdate(status="cancelled"))
    await db.commit()

    return ApiResponse(data={"success": True})


# ============ 批量校验接口 ============


@router.post("/batch", response_model=ApiResponse, summary="批量校验")
async def batch_check(
    file_ids: list[str],
    check_config: dict | None = None,
    operator: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """批量创建校验任务"""
    service = DocCheckService(db)
    operator = operator or (current_user.username if current_user else None)

    results = []
    for file_id in file_ids:
        if file_id not in _upload_store:
            continue

        upload_data = _upload_store[file_id]
        doc_type = upload_data.get("file_type", "SOP")

        # 创建校验任务
        check = await service.create_check(
            DocCheckCreate(
                doc_type=doc_type,
                doc_title=upload_data.get("file_name", ""),
                doc_content=upload_data.get("content", ""),
            ),
            operator=operator,
        )
        await db.commit()

        results.append(
            {
                "task_id": str(check.id),
                "status": check.status,
            }
        )

    return ApiResponse(
        data={
            "task_id": str(results[0]["task_id"]) if results else None,
            "status": "batch_created",
        }
    )


# ============ 记录列表接口 ============


@router.get("/records", response_model=ApiResponse, summary="获取校验记录列表")
async def get_records(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=200, description="每页数量"),
    status: str | None = Query(None, description="校验状态"),
    file_no: str | None = Query(None, description="文件编号"),
    file_type: str | None = Query(None, description="文件类型"),
    start_date: str | None = Query(None, description="开始日期"),
    end_date: str | None = Query(None, description="结束日期"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取校验记录列表"""
    service = DocCheckService(db)
    skip = (page - 1) * page_size

    checks, total = await service.get_checks(
        skip=skip,
        limit=page_size,
        status=status,
        doc_type=file_type,
    )

    # 转换格式
    items = []
    for check in checks:
        items.append(
            {
                "id": str(check.id),
                "file_name": check.file_name or "",
                "file_no": check.file_code,
                "file_version": check.file_version,
                "file_type": check.file_type,
                "preparer": check.operator,
                "prepare_date": check.created_at.isoformat()
                if check.created_at
                else None,
                "status": check.status,
                "total_problems": check.total_problems or 0,
                "risk_high": check.high_risk_count or 0,
                "risk_medium": check.medium_risk_count or 0,
                "risk_low": check.low_risk_count or 0,
                "operator": check.operator,
                "created_at": check.created_at.isoformat()
                if check.created_at
                else None,
                "updated_at": check.updated_at.isoformat()
                if check.updated_at
                else None,
            }
        )

    return ApiResponse(
        data={
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    )


@router.get(
    "/records/{record_id}", response_model=ApiResponse, summary="获取校验记录详情"
)
async def get_record_detail(
    record_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """获取校验记录详情"""
    service = DocCheckService(db)
    check = await service.get_check(record_id)

    if not check:
        return ApiResponse(code=404, message="校验记录不存在")

    # 获取问题列表
    problems = await service.get_problems(record_id)
    problems_data = []
    for prob in problems:
        problems_data.append(
            {
                "id": str(prob.id),
                "main_id": str(prob.check_main_id),
                "problem_type": prob.category,
                "risk_level": prob.severity,
                "location": prob.location,
                "description": prob.description,
                "suggestion": prob.suggestion,
                "handle_status": "pending",
                "created_at": prob.created_at.isoformat() if prob.created_at else None,
                "updated_at": prob.updated_at.isoformat() if prob.updated_at else None,
            }
        )

    return ApiResponse(
        data={
            "id": str(check.id),
            "file_name": check.file_name or "",
            "file_no": check.file_code,
            "file_version": check.file_version,
            "file_type": check.file_type,
            "preparer": check.operator,
            "prepare_date": check.created_at.isoformat() if check.created_at else None,
            "status": check.status,
            "total_problems": check.total_problems or 0,
            "risk_high": check.high_risk_count or 0,
            "risk_medium": check.medium_risk_count or 0,
            "risk_low": check.low_risk_count or 0,
            "operator": check.operator,
            "created_at": check.created_at.isoformat() if check.created_at else None,
            "updated_at": check.updated_at.isoformat() if check.updated_at else None,
            "problems": problems_data,
        }
    )


@router.post(
    "/records/{record_id}/confirm", response_model=ApiResponse, summary="确认通过"
)
async def confirm_check(
    record_id: uuid.UUID,
    operator: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """确认校验通过"""
    service = DocCheckService(db)
    operator = operator or (current_user.username if current_user else None)

    check = await service.get_check(record_id)
    if not check:
        return ApiResponse(code=404, message="校验记录不存在")

    if check.status != "completed":
        return ApiResponse(code=400, message="只有已完成状态的校验才能确认")

    await service.update_check(record_id, DocCheckUpdate(status="confirmed"))
    await db.commit()

    return ApiResponse(data={"success": True})


# ============ 问题处理接口 ============


@router.put("/problems/{problem_id}", response_model=ApiResponse, summary="更新问题")
async def update_problem(
    problem_id: uuid.UUID,
    data: ProblemUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """更新问题"""
    service = DocCheckService(db)
    operator = current_user.username if current_user else None

    # 获取问题（需要添加此方法）
    from app.modules.quality.qms.doc_check.repository import DocCheckRepository

    repo = DocCheckRepository(db)

    # 查找问题
    from sqlalchemy import select

    from app.modules.quality.qms.doc_check.models import DocCheckProblem

    result = await db.execute(
        select(DocCheckProblem).where(
            DocCheckProblem.id == problem_id,
            DocCheckProblem.is_deleted == False,
        )
    )
    problem = result.scalar_one_or_none()

    if not problem:
        return ApiResponse(code=404, message="问题不存在")

    # 更新问题
    if data.handle_status is not None:
        problem.handle_status = data.handle_status
    if data.ignore_reason is not None:
        problem.ignore_reason = data.ignore_reason
    if data.operator is not None:
        problem.operator = data.operator

    await db.commit()
    await db.refresh(problem)

    return ApiResponse(
        data={
            "id": str(problem.id),
            "handle_status": problem.handle_status,
            "ignore_reason": problem.ignore_reason,
        }
    )


@router.put("/problems/batch", response_model=ApiResponse, summary="批量更新问题")
async def batch_update_problems(
    problem_ids: list[str],
    handle_status: str,
    ignore_reason: str | None = None,
    operator: str | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """批量更新问题"""
    operator = operator or (current_user.username if current_user else None)

    from sqlalchemy import update

    from app.modules.quality.qms.doc_check.models import DocCheckProblem

    count = 0
    for problem_id in problem_ids:
        result = await db.execute(
            update(DocCheckProblem)
            .where(
                DocCheckProblem.id == uuid.UUID(problem_id),
                DocCheckProblem.is_deleted == False,
            )
            .values(
                handle_status=handle_status,
                ignore_reason=ignore_reason,
                operator=operator,
            )
        )
        if result.rowcount > 0:
            count += 1

    await db.commit()

    return ApiResponse(data={"success_count": count})


# ============ 导出报告接口 ============


@router.get("/export/{record_id}", response_model=ApiResponse, summary="导出校验报告")
async def export_report(
    record_id: uuid.UUID,
    format: str = Query("pdf", description="导出格式"),
    db: AsyncSession = Depends(get_db),
    current_user: CurrentUser | None = Depends(get_current_user),
):
    """导出校验报告"""
    service = DocCheckService(db)
    check = await service.get_check(record_id)

    if not check:
        return ApiResponse(code=404, message="校验记录不存在")

    # 生成报告（简化实现）
    file_name = f"{check.file_code or 'report'}_校验报告.{format}"

    return ApiResponse(
        data={
            "download_url": f"/api/v1/doc-check/download/{record_id}",
            "file_name": file_name,
        }
    )
