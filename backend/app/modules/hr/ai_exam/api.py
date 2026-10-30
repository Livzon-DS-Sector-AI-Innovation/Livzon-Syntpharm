"""AI exam API endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, Form, UploadFile
from fastapi.responses import StreamingResponse

from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.exceptions import AppException, BadRequestException
from app.core.job_store import start_job
from app.modules.hr.ai_exam.schemas import ExamExportRequest
from app.modules.hr.ai_exam.service import export_exam, generate_exam
from app.modules.hr.job_store import hr_job_store
from app.shared.schemas import AsyncJobAccepted, AsyncJobAcceptedResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["AI 出题"])

# 出题后台任务状态存 hr 模块共享的 hr_job_store；查询走 GET /api/v1/hr/jobs/{job_id}


@router.post("/generate", response_model=AsyncJobAcceptedResponse, summary="生成考试题目")
async def post(
    current_user: RequiredUser,
    file: UploadFile,
    ctx: PermissionContext = Depends(require_permission("hr:ai-exam:generate")),
    choice_count: int = Form(5),
    true_false_count: int = Form(5),
    multi_choice_count: int = Form(0),
    fill_blank_count: int = Form(0),
) -> Any:
    """提交出题后台任务（LLM 耗时 >5s）；轮询 GET /api/v1/hr/jobs/{job_id} 拿结果。"""
    if not file.filename:
        raise BadRequestException("文件名不能为空")
    logger.info(
        "Exam config: choice=%s tf=%s multi=%s fill=%s",
        choice_count,
        true_false_count,
        multi_choice_count,
        fill_blank_count,
    )
    config = {
        "choice_count": choice_count,
        "true_false_count": true_false_count,
        "multi_choice_count": multi_choice_count,
        "fill_blank_count": fill_blank_count,
    }
    content = await file.read()

    async def _run(_job: str) -> dict[str, Any]:
        try:
            result = await generate_exam(content, file.filename or "", config)
        except ValueError as e:
            raise RuntimeError(str(e)) from e
        except Exception as e:
            logger.exception("AI 出题失败")
            raise RuntimeError(f"AI 出题失败: {e}") from e
        return result

    job_id = start_job(hr_job_store, "hr-ai-exam", _run)
    return AsyncJobAcceptedResponse(data=AsyncJobAccepted(job_id=job_id))


@router.post("/export", summary="导出考试试卷")
async def api_export_exam(
    data: ExamExportRequest,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("hr:ai-exam:export")),
) -> Any:
    """将试卷导出为 Word 文档。"""
    try:
        buffer = export_exam(data.model_dump())
    except Exception as e:
        raise AppException(status_code=500, message=f'导出失败: {e}')

    from urllib.parse import quote

    safe_name = quote(f"考试试卷_{data.title}.docx")
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{safe_name}"},
    )
