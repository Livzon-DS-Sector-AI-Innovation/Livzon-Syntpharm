"""操作记录查询 API。

挂载前缀：/api/v1/audit（见 api/router.py）。
权限：`platform:audit:read`（与登录记录复用同一审计查看码，审计本身只读）。
"""

import csv
import io
import json
import uuid
from datetime import datetime
from urllib.parse import quote

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import PermissionContext, require_permission
from app.core.response import ApiResponse, build_response
from app.platform.audit.models import AuditLog
from app.platform.audit.schemas import AuditLogItem, AuditLogListData, AuditLogListResponse
from app.platform.identity.models import User

router = APIRouter(tags=["操作记录"])


@router.get("/logs", response_model=AuditLogListResponse, summary="查询操作记录")
async def list_audit_logs(
    ctx: PermissionContext = Depends(require_permission("platform:audit:read")),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID | None = Query(None, description="按操作者筛选"),
    action: str | None = Query(None, description="按动作筛选，如 user.update / grant.create"),
    resource_type: str | None = Query(None, description="按资源类型筛选，如 user / role / grant"),
    keyword: str | None = Query(None, description="按操作者姓名/账号模糊搜索"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> ApiResponse:
    """分页查询操作记录，按时间倒序。"""
    base = (
        select(AuditLog, User.name, User.username)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(AuditLog.action.isnot(None))
    )
    if user_id is not None:
        base = base.where(AuditLog.user_id == user_id)
    if action is not None:
        base = base.where(AuditLog.action == action)
    if resource_type is not None:
        base = base.where(AuditLog.resource_type == resource_type)
    if keyword:
        base = base.where(User.name.ilike(f"%{keyword}%") | User.username.ilike(f"%{keyword}%"))

    total = int((await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one())

    rows = (
        await db.execute(base.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size))
    ).all()

    data = [
        AuditLogItem(
            id=log.id,
            user_id=log.user_id,
            user_name=user_name,
            username=username,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            old_value=log.old_value,
            new_value=log.new_value,
            extra=log.extra,
            ip_address=log.ip_address,
            created_at=log.created_at,
        )
        for log, user_name, username in rows
    ]
    return build_response(data=AuditLogListData(items=data, total=total, page=page, page_size=page_size).model_dump())


@router.get("/logs/export", summary="导出操作记录（CSV）")
async def export_audit_logs(
    ctx: PermissionContext = Depends(require_permission("platform:audit:read")),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID | None = Query(None, description="按操作者筛选"),
    action: str | None = Query(None, description="按动作筛选"),
    resource_type: str | None = Query(None, description="按资源类型筛选"),
    keyword: str | None = Query(None, description="按操作者姓名/账号模糊搜索"),
) -> StreamingResponse:
    """按当前筛选条件导出操作记录为 CSV（最多 10000 条，按时间倒序）。"""
    limit = 10000

    base = (
        select(AuditLog, User.name, User.username)
        .outerjoin(User, User.id == AuditLog.user_id)
        .where(AuditLog.action.isnot(None))
    )
    if user_id is not None:
        base = base.where(AuditLog.user_id == user_id)
    if action is not None:
        base = base.where(AuditLog.action == action)
    if resource_type is not None:
        base = base.where(AuditLog.resource_type == resource_type)
    if keyword:
        base = base.where(User.name.ilike(f"%{keyword}%") | User.username.ilike(f"%{keyword}%"))

    rows = (await db.execute(base.order_by(AuditLog.created_at.desc()).limit(limit))).all()

    output = io.StringIO()
    writer = csv.writer(output)
    header = ["操作时间", "操作者", "账号", "动作", "资源类型", "资源ID", "IP", "改前", "改后", "附加信息"]
    writer.writerow(header)
    for log, user_name, username in rows:
        writer.writerow(
            [
                log.created_at.isoformat() if log.created_at else "",
                user_name or "",
                username or "",
                log.action or "",
                log.resource_type or "",
                str(log.resource_id) if log.resource_id else "",
                log.ip_address or "",
                json.dumps(log.old_value, ensure_ascii=False) if log.old_value else "",
                json.dumps(log.new_value, ensure_ascii=False) if log.new_value else "",
                json.dumps(log.extra, ensure_ascii=False) if log.extra else "",
            ]
        )

    # utf-8-sig 带 BOM，Excel 打开中文不乱码
    csv_bytes = output.getvalue().encode("utf-8-sig")
    filename = f"audit_logs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return StreamingResponse(
        iter([csv_bytes]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename*=utf-8''{quote(filename)}"},
    )
