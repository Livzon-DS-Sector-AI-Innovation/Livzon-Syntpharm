"""工作台聚合 API。

挂载前缀 ``/api/v1/workbench``（见 ``app/api/router.py``）。

该接口仅供登录用户读取自己的待办与流程：不单独挂权限码，内部按用户的
有效权限码逐数据源门控（无权限的源直接跳过，不返回任何数据）。
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import RequiredUser
from app.core.response import ApiResponse, build_response
from app.platform.workbench.read_marks import mark_reads
from app.platform.workbench.schemas import (
    TodoReadBatchRequest,
    TodoReadMark,
    TodoReadResultData,
    TodoReadResultResponse,
    WorkbenchOverviewResponse,
)
from app.platform.workbench.service import build_overview
from app.shared.workbench_types import OVERVIEW_ITEM_LIMIT_MAX, SOURCE_ITEM_LIMIT

router = APIRouter()


@router.get("/overview", response_model=WorkbenchOverviewResponse)
async def workbench_overview(
    user: RequiredUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    todo_limit: Annotated[int, Query(ge=1, le=OVERVIEW_ITEM_LIMIT_MAX)] = SOURCE_ITEM_LIMIT,
    process_limit: Annotated[int, Query(ge=1, le=OVERVIEW_ITEM_LIMIT_MAX)] = SOURCE_ITEM_LIMIT,
) -> ApiResponse:
    """首页工作台数据：审核待办 + 我参与的流程（含按模块分组的计数）。"""
    data = await build_overview(db, user, todo_limit=todo_limit, process_limit=process_limit)
    return build_response(data=data)


@router.post("/todos/read", response_model=TodoReadResultResponse)
async def mark_todo_read(
    payload: TodoReadMark,
    user: RequiredUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse:
    """标记单条待办已读（幂等）。

    只影响当前用户自己的铃铛计数，不改业务单据状态。
    """
    marked = await mark_reads(db, user.id, [payload])
    return build_response(data=TodoReadResultData(marked=marked))


@router.post("/todos/read-all", response_model=TodoReadResultResponse)
async def mark_all_todos_read(
    payload: TodoReadBatchRequest,
    user: RequiredUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ApiResponse:
    """一键已读：批量写入客户端当前看到的未读项（空列表直接返回 0）。"""
    marked = await mark_reads(db, user.id, payload.items)
    return build_response(data=TodoReadResultData(marked=marked))
