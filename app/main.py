import asyncio
import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

# Ensure platform models are registered in SQLAlchemy metadata
import app.platform.audit.models  # noqa: F401  # noqa: F401

# Ensure platform models are registered in SQLAlchemy metadata
import app.platform.identity.models  # noqa: F401
from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppException
from app.core.response import error_response
from app.modules.regulatory_tracker.tasks.sync_tasks import (
    start_scheduler,
)
from app.platform.audit import AuditMiddleware
from app.shared.ocr_service import init_ocr

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# 抑制第三方库的 DEBUG 日志噪音
logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("websockets").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# ── MCP 服务初始化（模块级别，确保 lifespan 可合并）──
from app.modules.equipment import mcp_tools  # noqa: E402, F401 — 触发 @mcp.tool() 注册
from app.platform.mcp.middleware import build_mcp_middleware  # noqa: E402
from app.platform.mcp.server import get_mcp_app  # noqa: E402

mcp_middleware = build_mcp_middleware()
mcp_asgi = get_mcp_app(path="/", middleware=mcp_middleware)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — auto-start all registered background workers."""
    logger.info("Starting %s (%s)", settings.APP_NAME, settings.APP_ENV)

    # Initialize OCR service
    init_ocr()

    # Import all modules to trigger their __init__.py and register workers
    import app.modules.energy  # noqa: F401
    import app.modules.equipment  # noqa: F401
    import app.modules.regulatory_tracker  # noqa: F401
    import app.modules.safety  # noqa: F401
    import app.platform.identity  # noqa: F401
    import app.platform.integrations.feishu  # noqa: F401

    # Start all registered background workers
    from app.shared.lifecycle import get_all_workers

    workers = get_all_workers()
    tasks = []

    for worker in workers:
        logger.info("Starting background worker: %s", worker.name)
        task = asyncio.create_task(worker.start())
        tasks.append((worker, task))

    # Start unified scheduler engine (for DB-driven generators)

    from app.modules.warehouse.feishu_events import register_feishu_event_handlers

    register_feishu_event_handlers()

    from app.modules.energy.scheduler import (
        energy_collection_loop,
    )
    from app.modules.equipment.scheduler import (
        maintenance_plan_loop,
        timeout_scan_loop,
    )
    from app.platform.identity.scheduler import (
        member_sync_loop,
    )

    start_scheduler()
    energy_task = asyncio.ensure_future(energy_collection_loop())
    maintenance_plan_task = asyncio.ensure_future(maintenance_plan_loop())
    timeout_task = asyncio.ensure_future(timeout_scan_loop())
    member_task = asyncio.ensure_future(member_sync_loop())

    # ── 平台级飞书 WebSocket 长连接 ──
    if settings.FEISHU_WS_ENABLED:
        from app.platform.integrations.feishu.event_handler import set_main_loop
        from app.platform.integrations.feishu.ws_client import start_ws_client

        set_main_loop(asyncio.get_running_loop())
        start_ws_client()

    # ── 仓储模块飞书 WebSocket 长连接（模块独立应用凭据） ──
    from app.modules.warehouse.ws_client import (
        set_main_loop as set_warehouse_ws_main_loop,
    )
    from app.modules.warehouse.ws_client import (
        start_ws_from_db as start_warehouse_ws,
    )

    set_warehouse_ws_main_loop(asyncio.get_running_loop())
    await start_warehouse_ws()

    # ── 设备模块飞书 WebSocket 长连接（独立交互机器人，原生 WebSocket） ──
    equipment_ws_task: asyncio.Task | None = None
    if settings.EQUIPMENT_FEISHU_APP_ID and settings.EQUIPMENT_FEISHU_APP_SECRET:
        from app.modules.equipment.feishu.ws_client import start_equipment_ws

        equipment_ws_task = asyncio.create_task(start_equipment_ws())

    # ── 安全模块专属飞书事件订阅（WebSocket 长连接，独立应用凭据）──
    from app.modules.safety.feishu.event_client import start_ws

    asyncio.create_task(start_ws())

    # ── 安全模块定时任务调度引擎 ──
    from app.modules.safety.scheduler import (
        scheduled_task_loop,
    )

    asyncio.create_task(scheduled_task_loop())

    # ── 统一调度引擎（平台级，各模块可渐进迁移）──

    from app.modules.equipment.scheduled import InspectionScheduleGenerator
    from app.platform.scheduler import SchedulerEngine, SchedulerRegistry

    scheduler_registry = SchedulerRegistry()
    scheduler_registry.register_generator(InspectionScheduleGenerator())

    # Register regulatory_tracker scheduled tasks
    from app.modules.regulatory_tracker.tasks.sync_tasks import (
        daily_ai_analysis_task,
        daily_sync_task,
    )

    scheduler_registry.register_task(daily_sync_task)
    scheduler_registry.register_task(daily_ai_analysis_task)
    scheduler_engine = SchedulerEngine(scheduler_registry)
    scheduler_engine_task = asyncio.create_task(scheduler_engine.run())

    logger.info(
        "Background tasks started (%d workers, %d generators)",
        len(workers),
        len(scheduler_registry.generators),
    )

    yield

    # Shutdown: stop all workers in reverse order
    logger.info("Shutting down %s", settings.APP_NAME)

    # Stop unified scheduler engine
    scheduler_engine.stop()
    try:
        await asyncio.wait_for(scheduler_engine_task, timeout=10)
    except (TimeoutError, asyncio.CancelledError):
        pass

    # Stop all background workers
    for worker, task in reversed(tasks):
        logger.info("Stopping background worker: %s", worker.name)
        if worker.stop:
            try:
                result = worker.stop()
                # Check if it's an awaitable (async function)
                if asyncio.iscoroutine(result):
                    await asyncio.wait_for(result, timeout=5)
            except (TimeoutError, asyncio.CancelledError):
                logger.warning("Worker %s stop timed out", worker.name)
        task.cancel()

    logger.info("Shutdown complete")

    # 停止设备模块 WebSocket
    if equipment_ws_task:
        from app.modules.equipment.feishu.ws_client import stop_equipment_ws

        await stop_equipment_ws()
        equipment_ws_task.cancel()

    from app.modules.warehouse.ws_client import stop_ws as stop_warehouse_ws

    await stop_warehouse_ws()

    energy_task.cancel()
    maintenance_plan_task.cancel()
    timeout_task.cancel()
    member_task.cancel()

    # 停止平台级飞书 WebSocket
    from app.platform.integrations.feishu.ws_client import stop_ws_client

    stop_ws_client()

    logger.info("Shutting down %s", settings.APP_NAME)


from fastmcp.utilities.lifespan import combine_lifespans  # noqa: E402

app = FastAPI(
    title=settings.APP_NAME,
    description="原料药事业部工厂基座系统",
    version="0.1.0",
    lifespan=combine_lifespans(lifespan, mcp_asgi.lifespan),
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(AuditMiddleware)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# 挂载静态文件目录（图片上传等）
uploads_dir = os.path.abspath(settings.UPLOAD_DIR)
os.makedirs(uploads_dir, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

# ── 挂载 MCP 服务（AI Agent 协议入口）──
app.mount("/mcp", mcp_asgi, name="mcp")
logger.info("MCP server mounted at /mcp")


@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return error_response(
        message=exc.message,
        detail=exc.detail_msg,
        status_code=exc.status_code,
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    return error_response(
        message=str(exc.detail),
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    errors = exc.errors()
    detail = "; ".join(f"{e.get('loc', [''])[-1]}: {e.get('msg', '')}" for e in errors)
    return error_response(
        message="请求参数校验失败",
        detail=detail,
        status_code=422,
    )


@app.exception_handler(IntegrityError)
async def integrity_error_handler(request: Request, exc: IntegrityError):
    msg = str(exc.orig) if hasattr(exc, "orig") else str(exc)
    # Extract constraint info for a user-friendly message
    if "duplicate key" in msg or "unique constraint" in msg:
        return error_response(
            message="数据重复，该记录已存在",
            detail=msg,
            status_code=409,
        )
    return error_response(
        message="数据完整性错误",
        detail=msg,
        status_code=400,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
