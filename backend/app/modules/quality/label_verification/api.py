# mypy: ignore-errors
import asyncio
import logging

logger = logging.getLogger(__name__)

from datetime import date  # noqa: E402
from typing import Any  # noqa: E402
from uuid import UUID  # noqa: E402

from fastapi import Depends, Query, UploadFile  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession  # noqa: E402

from app.core.database import get_db  # noqa: E402
from app.core.deps import PermissionContext, RequiredUser, require_permission  # noqa: E402
from app.core.job_store import JobStore, get_job_state_or_404, start_job  # noqa: E402
from app.core.response import build_response, paginated_response  # noqa: E402
from app.shared.module_api import create_module_router  # noqa: E402
from app.shared.module_registry import MODULES_BY_CODE  # noqa: E402
from app.shared.schemas import (  # noqa: E402
    AsyncJobAccepted,
    AsyncJobAcceptedResponse,
    AsyncJobStateResponse,
    PageParams,
)

from .schemas import (  # noqa: E402
    LabelVerificationCreate,
    LabelVerificationUpdate,
)
from .service import LabelVerificationService  # noqa: E402

router = create_module_router(MODULES_BY_CODE["quality"])


def get_label_verification_service(
    session: AsyncSession = Depends(get_db),
) -> LabelVerificationService:
    return LabelVerificationService(session)


# ─── LabelVerification Routes ───


@router.get("/label-verifications", summary="标签复核记录列表")
async def get(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:read")),
    batch_number: str | None = Query(None, description="批号搜索"),
    product_name: str | None = Query(None, description="产品名称搜索"),
    result_status: str | None = Query(None, description="结论状态筛选"),
    start_date: date | None = Query(None, description="复核日期起始"),
    end_date: date | None = Query(None, description="复核日期截止"),
    page_params: PageParams = Depends(),
    service: LabelVerificationService = Depends(get_label_verification_service),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    verifications, total = await service.list_verifications(
        batch_number=batch_number,
        product_name=product_name,
        result_status=result_status,
        start_date=start_date,
        end_date=end_date,
        page=page_params.page,
        page_size=page_params.page_size,
    )

    data = [v.model_dump(mode="json") for v in verifications]

    return paginated_response(
        data=data,
        page=page_params.page,
        page_size=page_params.page_size,
        total=total,
    )


@router.post("/label-verifications", summary="创建标签复核记录")
async def post(
    current_user: RequiredUser,
    payload: LabelVerificationCreate,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:create")),
    service: LabelVerificationService = Depends(get_label_verification_service),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    verification = await service.create_verification(payload)

    return build_response(
        data=verification.model_dump(mode="json"),
        message="标签复核记录创建成功",
        code=201,
    )


@router.get("/label-verifications/statistics", summary="标签复核统计")  # type: ignore[no-redef]
async def get(  # noqa: F811
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:read")),
    service: LabelVerificationService = Depends(get_label_verification_service),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    stats = await service.get_statistics()

    return build_response(data=stats.model_dump(mode="json"))


@router.get(
    "/label-verifications/batch/{batch_number}",
    summary="按批号查询历史记录",
)
async def handler(
    current_user: RequiredUser,
    batch_number: str,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:read")),
    service: LabelVerificationService = Depends(get_label_verification_service),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    verifications = await service.get_by_batch_number(batch_number)

    data = [v.model_dump(mode="json") for v in verifications]

    return build_response(data=data)


@router.get(  # type: ignore[no-redef]
    "/label-verifications/{verification_id}",
    summary="标签复核记录详情",
)
async def handler(  # noqa: F811
    current_user: RequiredUser,
    verification_id: UUID,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:read")),
    service: LabelVerificationService = Depends(get_label_verification_service),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    verification = await service.get_verification(verification_id)

    return build_response(
        data=verification.model_dump(mode="json"),
    )


@router.put(  # type: ignore[no-redef]
    "/label-verifications/{verification_id}",
    summary="更新标签复核记录",
)
async def handler(  # noqa: F811
    current_user: RequiredUser,
    verification_id: UUID,
    payload: LabelVerificationUpdate,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:update")),
    service: LabelVerificationService = Depends(get_label_verification_service),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    verification = await service.update_verification(verification_id, payload)

    return build_response(
        data=verification.model_dump(mode="json"),
        message="标签复核记录更新成功",
    )


@router.delete(  # type: ignore[no-redef]
    "/label-verifications/{verification_id}",
    summary="删除标签复核记录",
)
async def handler(  # noqa: F811
    current_user: RequiredUser,
    verification_id: UUID,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:delete")),
    service: LabelVerificationService = Depends(get_label_verification_service),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    await service.delete_verification(verification_id)

    return build_response(message="标签复核记录删除成功")


@router.post(  # type: ignore[no-redef]
    "/label-verifications/upload-video",
    summary="上传标签复核视频",
)
async def handler(  # noqa: F811
    current_user: RequiredUser,
    file: UploadFile,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:create")),
    service: LabelVerificationService = Depends(get_label_verification_service),
) -> Any:  # noqa: F821  # type: ignore[name-defined]
    """上传视频文件，返回文件 key 和文件名"""

    import os
    from datetime import datetime

    from app.core.config import get_settings

    settings = get_settings()

    upload_dir = os.path.join(settings.UPLOAD_DIR, "label-verification")

    os.makedirs(upload_dir, exist_ok=True)

    os.path.splitext(file.filename or ".mp4")[1]

    timestamp = int(datetime.now().timestamp())

    safe_name = f"video_{timestamp}_{file.filename or 'unknown'}"

    file_path = os.path.join(upload_dir, safe_name)

    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    file_key = f"label-verification/{safe_name}"

    return build_response(
        data={
            "file_key": file_key,
            "file_name": file.filename or safe_name,
            "file_size": len(content),
        },
        message="视频上传成功",
    )


# ─── 视频分析后台任务（抽帧 + vision LLM 耗时 >5s，改为提交任务 + 轮询） ───

from pydantic import BaseModel, Field  # noqa: E402

_label_job_store = JobStore()


async def _run_analyze_video(job_id: str, file_key: str, fps: float) -> dict[str, Any]:
    """视频标签识别（后台执行）：抽帧 → vision LLM → JSON 解析。"""
    import json
    import os

    from app.core.config import get_settings
    from app.core.llm import llm_client
    from app.core.llm.exceptions import LLMOutputError, LLMProviderError, LLMRateLimitError

    from .video_service import LabelVerificationVideoService

    settings = get_settings()
    video_path = os.path.join(settings.UPLOAD_DIR, file_key)
    if not os.path.exists(video_path):
        raise RuntimeError("视频文件不存在")

    video_service = LabelVerificationVideoService(settings.UPLOAD_DIR)
    # OpenCV 抽帧是同步阻塞调用，放线程池执行，避免卡住事件循环（其他请求会一起变慢）
    frames = await asyncio.to_thread(video_service.extract_frames, video_path, fps, 20)
    if not frames:
        raise RuntimeError("无法从视频中提取帧")

    prompt = """请仔细分析这张图片中的标签信息，提取以下内容并以 JSON 格式返回：

{

  "batch_number": "批号",

  "product_name": "产品名称",

  "production_date": "生产日期 (YYYY-MM-DD)",

  "expiry_date": "有效期至 (YYYY-MM-DD)",

  "total_barrels": 总桶数 (数字),

  "standard_barrels": 整桶数 (数字),

  "remainder_barrel": 零头桶数 (0或1),

  "standard_weight": 整桶重量 (数字，单位kg),

  "remainder_weight": 零头重量 (数字，单位kg),

  "total_weight": 总重量 (数字，单位kg),

  "confidence": 识别置信度 (0-100),

  "notes": "备注说明"

}



如果某些信息无法识别，请将其设为 null。请确保返回有效的 JSON。"""

    # 使用第一帧和最后一帧进行分析
    images_to_analyze = [frames[0]]
    if len(frames) > 1:
        images_to_analyze.append(frames[-1])

    try:
        result = await llm_client.chat_vision(prompt, images_to_analyze)
    except (LLMOutputError, LLMProviderError, LLMRateLimitError) as e:
        logger.exception("LLM call failed")
        return {
            "frames_extracted": len(frames),
            "fps_used": fps,
            "ai_result": {"error": str(e), "raw_response": None},
            "degraded": "AI 分析暂时不可用，请人工审核",
        }

    try:
        cleaned = result.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        ai_result = json.loads(cleaned.strip())
    except json.JSONDecodeError:
        ai_result = {"raw_response": result, "error": "JSON 解析失败"}

    return {"frames_extracted": len(frames), "fps_used": fps, "ai_result": ai_result}


class AutoCompareRequest(BaseModel):
    """自动对比请求体"""

    video_file_key: str = Field(..., description="视频文件 key")
    batch_number: str = Field(..., description="批号")
    product_name: str = Field("", description="产品名称")
    production_date: str = Field("", description="生产日期")
    expiry_date: str = Field("", description="有效期至")
    total_barrels: int | None = Field(None, description="总桶数")
    standard_barrels: int | None = Field(None, description="整桶数")
    remainder_barrel: int | None = Field(None, description="零头桶数")
    standard_weight: float | None = Field(None, description="整桶重量")
    remainder_weight: float | None = Field(None, description="零头重量")
    total_weight: float | None = Field(None, description="总重量")


async def _run_auto_compare(job_id: str, payload: AutoCompareRequest) -> dict[str, Any]:
    """自动对比（后台执行）：识别不全自动降帧率重析，返回 8 项核对结论。"""
    import os

    from app.core.config import get_settings
    from app.core.llm import llm_client

    from .video_service import LabelVerificationVideoService

    settings = get_settings()
    video_path = os.path.join(settings.UPLOAD_DIR, payload.video_file_key)
    if not os.path.exists(video_path):
        # 尝试 label-verification 子目录
        video_path = os.path.join(
            settings.UPLOAD_DIR,
            "label-verification",
            os.path.basename(payload.video_file_key),
        )
        if not os.path.exists(video_path):
            raise RuntimeError("视频文件不存在")

    form_data = {
        "batch_number": payload.batch_number,
        "product_name": payload.product_name,
        "production_date": payload.production_date,
        "expiry_date": payload.expiry_date,
        "total_barrels": payload.total_barrels,
        "standard_barrels": payload.standard_barrels,
        "remainder_barrel": payload.remainder_barrel,
        "standard_weight": payload.standard_weight,
        "remainder_weight": payload.remainder_weight,
        "total_weight": payload.total_weight,
    }

    video_service = LabelVerificationVideoService(settings.UPLOAD_DIR)
    return await video_service.analyze_and_compare(
        video_path=video_path,
        form_data=form_data,
        ai_service=llm_client,
    )


@router.post(
    "/label-verifications/analyze-video",
    response_model=AsyncJobAcceptedResponse,
    summary="提交标签复核视频分析任务",
)
async def handler(  # noqa: F811
    current_user: RequiredUser,
    file_key: str,
    fps: float = 1.0,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:create")),
) -> AsyncJobAcceptedResponse:
    """提交视频标签识别后台任务；轮询 GET /label-verifications/jobs/{job_id} 拿结果。"""
    job_id = start_job(
        _label_job_store,
        "label-verification-analyze",
        lambda _job: _run_analyze_video(_job, file_key, fps),
    )
    return AsyncJobAcceptedResponse(data=AsyncJobAccepted(job_id=job_id))


@router.post(
    "/label-verifications/auto-compare",
    response_model=AsyncJobAcceptedResponse,
    summary="提交视频与表单数据自动对比任务",
)
async def auto_compare_handler(  # noqa: F811
    current_user: RequiredUser,
    payload: AutoCompareRequest,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:create")),
) -> AsyncJobAcceptedResponse:
    """提交自动对比后台任务；轮询 GET /label-verifications/jobs/{job_id} 拿结果。"""
    job_id = start_job(
        _label_job_store,
        "label-verification-compare",
        lambda _job: _run_auto_compare(_job, payload),
    )
    return AsyncJobAcceptedResponse(data=AsyncJobAccepted(job_id=job_id))


@router.get(
    "/label-verifications/jobs/{job_id}",
    response_model=AsyncJobStateResponse,
    summary="查询视频分析/对比任务状态",
)
async def get_label_job_status(
    job_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:label-verification:read")),
) -> AsyncJobStateResponse:
    return AsyncJobStateResponse(data=get_job_state_or_404(_label_job_store, job_id))
