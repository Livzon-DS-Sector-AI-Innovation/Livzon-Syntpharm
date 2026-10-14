"""系统运维 API（只读探测 + Redis 缓存清理）。

挂载前缀：/api/v1/system（见 api/router.py）。
"""

from fastapi import APIRouter, Depends, Query, Request

from app.core.deps import PermissionContext, require_permission
from app.core.exceptions import BadRequestException
from app.platform.system import api_switch_service, ops_service
from app.platform.system.ops_schemas import (
    ApiRouteItemModel,
    ApiRoutesResponse,
    ApiSwitchRequest,
    ApiSwitchResponse,
    ApiSwitchResult,
    DbColumnsResponse,
    DbTablesResponse,
    HealthResponse,
    LogClearResult,
    LogItemModel,
    LogsClearResponse,
    LogsData,
    LogsResponse,
    RedisDeleteResponse,
    RedisKeysResponse,
    RedisOverviewResponse,
    ResourcesResponse,
    ScheduledTasksResponse,
    SystemInfoResponse,
)
from app.shared import log_buffer

router = APIRouter(tags=["系统运维"])


@router.get("/health", response_model=HealthResponse, summary="服务健康检查")
async def system_health(
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> HealthResponse:
    """并行探测 backend / postgres / redis / minio 的存活与耗时。"""
    return HealthResponse(data=await ops_service.check_services())


@router.get("/info", response_model=SystemInfoResponse, summary="系统信息")
async def system_info(
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> SystemInfoResponse:
    """版本、环境标识、Python 与关键依赖版本、运行时长。"""
    return SystemInfoResponse(data=ops_service.get_system_info())


@router.get("/resources", response_model=ResourcesResponse, summary="资源监控")
async def system_resources(
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> ResourcesResponse:
    """磁盘 / 内存 / 负载（容器视角，容器内读到的为宿主机资源）。"""
    return ResourcesResponse(data=ops_service.get_resources())


@router.get("/redis", response_model=RedisOverviewResponse, summary="Redis 概览")
async def system_redis_overview(
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> RedisOverviewResponse:
    """key 总数、内存占用、连接数、命中率。"""
    return RedisOverviewResponse(data=await ops_service.get_redis_overview())


@router.get("/redis/keys", response_model=RedisKeysResponse, summary="按前缀查看 Redis key")
async def system_redis_keys(
    prefix: str = Query("", max_length=200, description="key 前缀，留空为全部"),
    limit: int = Query(200, ge=1, le=1000),
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> RedisKeysResponse:
    """SCAN 遍历（非 KEYS），最多返回 limit 个。"""
    return RedisKeysResponse(data=await ops_service.list_redis_keys(prefix, limit))


@router.delete("/redis/keys", response_model=RedisDeleteResponse, summary="按前缀清理 Redis key")
async def system_redis_delete(
    prefix: str = Query(..., min_length=2, max_length=200, description="key 前缀（至少 2 字符）"),
    ctx: PermissionContext = Depends(require_permission("platform:ops:manage")),
) -> RedisDeleteResponse:
    """按前缀清理缓存。禁止空/过短前缀，防误删全库。"""
    try:
        result = await ops_service.delete_redis_keys(prefix)
    except ValueError as exc:
        raise BadRequestException(str(exc)) from exc
    return RedisDeleteResponse(data=result)


@router.get("/scheduled-tasks", response_model=ScheduledTasksResponse, summary="定时任务 / 后台任务清单")
async def system_scheduled_tasks(
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> ScheduledTasksResponse:
    """汇总调度引擎任务、动态生成器、后台 worker 与独立轮询循环。"""
    return ScheduledTasksResponse(data=ops_service.list_scheduled_tasks())


# ── API 启停开关 ──────────────────────────────────────────────────


@router.get("/api-routes", response_model=ApiRoutesResponse, summary="全部 API 清单与启停状态")
async def system_api_routes(
    request: Request,
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> ApiRoutesResponse:
    """从 OpenAPI schema 导出全部接口（自动跟随代码），含禁用状态与保护标记。"""
    items = api_switch_service.list_api_routes(request.app)
    return ApiRoutesResponse(
        data=[ApiRouteItemModel(**item.__dict__) for item in items],
    )


@router.put("/api-routes/switch", response_model=ApiSwitchResponse, summary="启用 / 禁用某个接口")
async def system_api_switch(
    payload: ApiSwitchRequest,
    ctx: PermissionContext = Depends(require_permission("platform:ops:manage")),
) -> ApiSwitchResponse:
    """禁用后该接口立即 403（内存判定，无需重启）；保护名单内接口拒绝禁用。"""
    try:
        await api_switch_service.set_switch(
            payload.method,
            payload.route,
            payload.enabled,
            payload.reason,
            ctx.user.id,
        )
    except ValueError as exc:
        raise BadRequestException(str(exc)) from exc

    return ApiSwitchResponse(
        data=ApiSwitchResult(
            method=payload.method.upper(),
            route=payload.route,
            enabled=payload.enabled,
            message="已启用" if payload.enabled else "已禁用",
        )
    )


# ── 日志管理 ──────────────────────────────────────────────────────


@router.get("/logs", response_model=LogsResponse, summary="运行日志（内存缓冲）")
async def system_logs(
    level: str = Query("", max_length=100, description="级别过滤，逗号分隔：INFO,ERROR"),
    keyword: str = Query("", max_length=200, description="关键词（消息 / logger 名）"),
    limit: int = Query(500, ge=1, le=2000),
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> LogsResponse:
    """返回最近的运行日志（内存环形缓冲，最多 2000 条，重启清空；时间倒序，最新在前）。"""
    items = log_buffer.query_logs(level, keyword, limit)
    return LogsResponse(
        data=LogsData(
            items=[LogItemModel(**item.__dict__) for item in items],
            total=len(items),
            buffer_size=log_buffer.buffer_size(),
        )
    )


@router.delete("/logs", response_model=LogsClearResponse, summary="清空日志缓冲")
async def system_logs_clear(
    ctx: PermissionContext = Depends(require_permission("platform:ops:manage")),
) -> LogsClearResponse:
    """清空内存缓冲区（仅影响本进程缓冲，不影响容器 stdout 日志）。"""
    cleared = log_buffer.clear_logs()
    return LogsClearResponse(data=LogClearResult(cleared=cleared))


# ── 数据库信息（只读：表结构 / 体积 / 行数估算） ────────────────────
#
# 红线：只暴露**结构**，不返回任何一行的数据内容。


@router.get("/db/tables", response_model=DbTablesResponse, summary="数据库概览与表清单")
async def system_db_tables(
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> DbTablesResponse:
    """库版本 / 大小 / 连接数 / 缓存命中率 + 全部业务表（体积、行数估算、列数）。"""
    return DbTablesResponse(data=await ops_service.get_db_tables())


@router.get(
    "/db/tables/{schema}/{table}/columns",
    response_model=DbColumnsResponse,
    summary="表字段结构",
)
async def system_db_table_columns(
    schema: str,
    table: str,
    ctx: PermissionContext = Depends(require_permission("platform:ops:read")),
) -> DbColumnsResponse:
    """单表字段结构（列名 / 类型 / 可空 / 默认值 / 注释）。表不存在返回 400。"""
    return DbColumnsResponse(data=await ops_service.get_db_table_columns(schema, table))
