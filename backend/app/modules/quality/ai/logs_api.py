"""AI 交互日志查询 API。

单独成文件而不是并入 ``ai/api.py``：后者顶部依赖 ``administration`` 模块的
模型，而该模块目前是空壳（``models.py`` 只有 TODO），一旦被 ``api/router.py``
导入就会在启动时抛 ImportError。日志查询只依赖 identity 权限与自身 service，
放在这里可以安全挂载。
"""

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, RequiredUser, require_permission
from app.core.response import build_response
from app.modules.quality.ai.models import QmsAiLog
from app.modules.quality.ai.schemas import (
    AiLogDetailApiResponse,
    AiLogItem,
    AiLogPaginatedListApiResponse,
    AiLogPaginatedListResponse,
)
from app.modules.quality.ai.service import AiLogService

logger = logging.getLogger(__name__)

router = APIRouter()


def _to_item(log: QmsAiLog) -> AiLogItem:
    """把 ORM 实体转成响应模型。"""
    return AiLogItem(
        id=str(log.id),
        bill_no=log.bill_no,
        operate_type=log.operate_type,
        operator=log.operator,
        system_prompt=log.system_prompt,
        user_input=log.user_input,
        ai_response=log.ai_response,
        error_message=log.error_message,
        tokens_used=log.tokens_used,
        latency_ms=log.latency_ms,
        created_at=log.created_at.isoformat() if log.created_at else "",
    )


def _parse_date(value: str, field: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=f"{field}格式应为 YYYY-MM-DD") from exc


@router.get("/logs", response_model=AiLogPaginatedListApiResponse, summary="查询 AI 交互日志")
async def list_ai_logs(
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:ai-log:read")),
    operate_type: str | None = Query(None, description="操作类型"),
    operator: str | None = Query(None, description="操作人账号"),
    keyword: str | None = Query(None, description="关键字（操作类型/操作人/单据编号模糊匹配）"),
    start_date: str | None = Query(None, description="开始日期，格式 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期，格式 YYYY-MM-DD"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """查询 AI 交互日志列表，按创建时间倒序。"""
    start_dt = _parse_date(start_date, "开始日期") if start_date else None
    end_dt = _parse_date(end_date, "结束日期").replace(hour=23, minute=59, second=59) if end_date else None

    logs, total = await AiLogService(session).list_logs(
        operate_type=operate_type,
        operator=operator,
        keyword=keyword,
        start_date=start_dt,
        end_date=end_dt,
        page=page,
        page_size=page_size,
    )

    return build_response(
        data=AiLogPaginatedListResponse(
            items=[_to_item(log) for log in logs],
            total=total,
            page=page,
            page_size=page_size,
        ),
    )


@router.get("/logs/{log_id}", response_model=AiLogDetailApiResponse, summary="查询 AI 交互日志详情")
async def get_ai_log(
    log_id: str,
    current_user: RequiredUser,
    ctx: PermissionContext = Depends(require_permission("quality:ai-log:read")),
    session: AsyncSession = Depends(get_db),
) -> Any:
    """按 ID 查询单条 AI 交互日志。"""
    try:
        log_uuid = uuid.UUID(log_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="日志 ID 格式不正确") from exc

    log = await AiLogService(session).get_by_id(log_uuid)
    if log is None:
        raise HTTPException(status_code=404, detail="AI 交互日志不存在")
    return build_response(data=_to_item(log))
