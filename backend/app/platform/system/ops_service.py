"""系统运维探测服务：健康检查、系统信息、资源、Redis、任务清单。

全部为只读探测（Redis 清理为唯一写操作），不依赖业务模块。
"""

import asyncio
import importlib.metadata as md
import os
import shutil
import sys
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from app.core.config import get_settings
from app.core.database import engine
from app.core.exceptions import BadRequestException
from app.core.redis import redis_client
from app.platform.system.ops_schemas import (
    ComponentHealth,
    DbColumnItem,
    DbColumnsData,
    DbOverview,
    DbTableItem,
    DbTablesData,
    DependencyInfo,
    DiskUsage,
    LoadAverage,
    MemoryUsage,
    RedisDeleteResult,
    RedisKeysData,
    RedisOverviewData,
    ResourcesData,
    ScheduledTaskItem,
    SystemInfoData,
)

APP_VERSION = "0.1.0"
_STARTED_AT = datetime.now(UTC)

_TRACKED_DEPENDENCIES = (
    "fastapi",
    "uvicorn",
    "sqlalchemy",
    "asyncpg",
    "pydantic",
    "alembic",
    "redis",
    "httpx",
)

# 独立轮询循环（main.py lifespan 里 asyncio.ensure_future 启动，不经 SchedulerRegistry）
_STANDALONE_LOOPS: tuple[tuple[str, str, str], ...] = (
    ("energy_collection_loop", "interval 300s", "能耗数据自动采集"),
    ("maintenance_plan_loop", "interval 60s", "设备保养计划生成"),
    ("timeout_scan_loop", "interval 60s", "设备工单超时扫描"),
    ("member_sync_loop", "interval 按配置", "飞书组织成员同步"),
)


# ── 服务健康 ──────────────────────────────────────────────────────


async def _check_postgres() -> ComponentHealth:
    start = time.perf_counter()
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            # 实例启动时刻 → 运行时长（pg_postmaster_start_time = 数据库实例启动时间）
            uptime = (
                await conn.execute(text("SELECT EXTRACT(EPOCH FROM (now() - pg_postmaster_start_time()))::bigint"))
            ).scalar()
        return ComponentHealth(
            name="postgres",
            status="ok",
            latency_ms=_elapsed_ms(start),
            uptime_seconds=int(uptime) if uptime is not None else None,
        )
    except Exception as exc:  # noqa: BLE001 - 探测失败原因要回显
        return ComponentHealth(name="postgres", status="error", detail=str(exc)[:300])


async def _check_redis() -> ComponentHealth:
    start = time.perf_counter()
    try:
        await asyncio.wait_for(redis_client.ping(), timeout=3.0)
        info = await asyncio.wait_for(redis_client.info(), timeout=3.0)
        uptime = info.get("uptime_in_seconds") if isinstance(info, dict) else None
        return ComponentHealth(
            name="redis",
            status="ok",
            latency_ms=_elapsed_ms(start),
            uptime_seconds=int(uptime) if uptime is not None else None,
        )
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth(name="redis", status="error", detail=str(exc)[:300])


async def _check_minio() -> ComponentHealth:
    from app.core.storage import is_enabled

    if not is_enabled():
        return ComponentHealth(name="minio", status="disabled", detail="未启用（MINIO_ENABLED=false）")

    settings = get_settings()

    def _probe() -> int:
        from minio import Minio

        client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        return len(client.list_buckets())

    start = time.perf_counter()
    try:
        bucket_count = await asyncio.wait_for(asyncio.to_thread(_probe), timeout=5.0)
        return ComponentHealth(
            name="minio",
            status="ok",
            latency_ms=_elapsed_ms(start),
            detail=f"{bucket_count} 个 bucket",
        )
    except Exception as exc:  # noqa: BLE001
        return ComponentHealth(name="minio", status="error", detail=str(exc)[:300])


async def check_services() -> list[ComponentHealth]:
    """并行探测各依赖组件。"""
    results = await asyncio.gather(
        _check_postgres(),
        _check_redis(),
        _check_minio(),
    )
    backend = ComponentHealth(
        name="backend",
        status="ok",
        uptime_seconds=_uptime_seconds(),
    )
    return [backend, *results]


# ── 系统信息 ──────────────────────────────────────────────────────


def get_system_info() -> SystemInfoData:
    settings = get_settings()
    deps: list[DependencyInfo] = []
    for name in _TRACKED_DEPENDENCIES:
        try:
            version = md.version(name)
        except md.PackageNotFoundError:
            version = "unknown"
        deps.append(DependencyInfo(name=name, version=version))

    return SystemInfoData(
        app_name=settings.APP_NAME,
        app_env=settings.APP_ENV,
        version=APP_VERSION,
        python_version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        started_at=_STARTED_AT.isoformat(),
        uptime_seconds=_uptime_seconds(),
        dependencies=deps,
    )


# ── 资源监控 ──────────────────────────────────────────────────────


def get_resources() -> ResourcesData:
    disk_path = "/"
    usage = shutil.disk_usage(disk_path)
    gb = 1024**3
    disk = DiskUsage(
        path=disk_path,
        total_gb=round(usage.total / gb, 2),
        used_gb=round(usage.used / gb, 2),
        free_gb=round(usage.free / gb, 2),
        percent=round(usage.used / usage.total * 100, 1) if usage.total else 0.0,
    )

    total_kb, available_kb = _read_meminfo()
    if total_kb:
        used_kb = total_kb - available_kb
        memory = MemoryUsage(
            total_gb=round(total_kb / 1024 / 1024, 2),
            used_gb=round(used_kb / 1024 / 1024, 2),
            available_gb=round(available_kb / 1024 / 1024, 2),
            percent=round(used_kb / total_kb * 100, 1),
        )
    else:
        memory = MemoryUsage(total_gb=0.0, used_gb=0.0, available_gb=0.0, percent=0.0)

    try:
        load1, load5, load15 = os.getloadavg()
    except OSError:
        load1 = load5 = load15 = 0.0
    load = LoadAverage(load1=load1, load5=load5, load15=load15, cpu_count=os.cpu_count() or 0)

    return ResourcesData(disk=disk, memory=memory, load=load)


def _read_meminfo() -> tuple[int, int]:
    """读取 /proc/meminfo，返回 (MemTotal_kB, MemAvailable_kB)；失败返回 (0, 0)。"""
    try:
        values: dict[str, int] = {}
        with open("/proc/meminfo", encoding="utf-8") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                if rest:
                    values[key.strip()] = int(rest.strip().split()[0])
        return values.get("MemTotal", 0), values.get("MemAvailable", 0)
    except Exception:  # noqa: BLE001 - 非 Linux 或权限不足时静默降级
        return 0, 0


# ── Redis ─────────────────────────────────────────────────────────


async def get_redis_overview() -> RedisOverviewData:
    info = await redis_client.info()
    dbsize = int(await redis_client.dbsize())
    return RedisOverviewData(
        dbsize=dbsize,
        used_memory_human=str(info.get("used_memory_human", "-")),
        connected_clients=int(info.get("connected_clients", 0)),
        keyspace_hits=int(info.get("keyspace_hits", 0)),
        keyspace_misses=int(info.get("keyspace_misses", 0)),
        uptime_in_days=int(info.get("uptime_in_days", 0)),
        version=str(info.get("redis_version", "-")),
    )


async def list_redis_keys(prefix: str, limit: int = 200) -> RedisKeysData:
    keys: list[str] = []
    truncated = False
    pattern = f"{prefix}*" if prefix else "*"
    async for key in redis_client.scan_iter(match=pattern, count=200):
        keys.append(str(key))
        if len(keys) >= limit:
            truncated = True
            break
    return RedisKeysData(keys=sorted(keys), total_scanned=len(keys), truncated=truncated)


async def delete_redis_keys(prefix: str) -> RedisDeleteResult:
    """按前缀清理 key。禁止空/过短前缀，防误删全库。"""
    if len(prefix) < 2:
        raise ValueError("前缀至少 2 个字符，禁止全库清理")

    deleted = 0
    async for key in redis_client.scan_iter(match=f"{prefix}*", count=200):
        await redis_client.delete(key)
        deleted += 1
    return RedisDeleteResult(deleted=deleted, pattern=f"{prefix}*")


# ── 定时任务 / 后台任务清单 ───────────────────────────────────────


def list_scheduled_tasks() -> list[ScheduledTaskItem]:
    items: list[ScheduledTaskItem] = []

    # 1) SchedulerEngine 注册的任务与生成器（代码注册）
    from app.platform.scheduler.registry import get_global_registry

    registry = get_global_registry()
    if registry is not None:
        for name, task in registry.tasks.items():
            items.append(
                ScheduledTaskItem(
                    name=name,
                    kind="task",
                    schedule=_describe_schedule(task.schedule),
                    module=task.module,
                    enabled=task.enabled and not registry.is_disabled(name),
                )
            )
        for name, gen in registry.generators.items():
            items.append(
                ScheduledTaskItem(
                    name=name,
                    kind="generator",
                    schedule=_describe_schedule(gen.schedule),
                    enabled=gen.enabled and not registry.is_disabled(name),
                )
            )

    # 2) 注册的后台 worker（WebSocket 长连接等）
    from app.shared.lifecycle import get_all_workers

    for worker in get_all_workers():
        items.append(
            ScheduledTaskItem(
                name=worker.name,
                kind="worker",
                schedule="长驻进程",
                description="模块注册的后台工作进程",
            )
        )

    # 3) main.py 直起的独立轮询循环（静态登记）
    for name, schedule, description in _STANDALONE_LOOPS:
        items.append(
            ScheduledTaskItem(name=name, kind="loop", schedule=schedule, description=description),
        )

    return items


def set_task_enabled(name: str, enabled: bool) -> bool:
    """运行时临时启停一个定时任务 / 生成器（内存态，容器重启后恢复默认）。

    返回是否找到并生效；找不到（名字不存在或 registry 未初始化）返回 False。
    """
    from app.platform.scheduler.registry import get_global_registry

    registry = get_global_registry()
    if registry is None:
        return False
    if name not in registry.tasks and name not in registry.generators:
        return False
    if enabled:
        registry.enable(name)
    else:
        registry.disable(name)
    return True


def _describe_schedule(schedule: Any) -> str:
    strategy = getattr(schedule, "strategy", None)
    value = getattr(strategy, "value", str(strategy))
    if value == "cron":
        return f"cron {schedule.expression}"
    if value == "interval":
        return f"interval {schedule.interval_seconds}s"
    if value == "fixed_time":
        return f"每天 {schedule.time_of_day}"
    return value


# ── 数据库信息（只读：概览 / 表清单 / 字段结构） ────────────────────
#
# 全部走 PostgreSQL 内置统计视图，**不扫表**（毫秒级），也不返回任何数据内容。
# 行数用 `pg_stat_user_tables.n_live_tup`（估算，ANALYZE 后准确）；
# 对千万行表用 count(*) 会全表扫描拖慢库，故一律用估算值并在界面标注。

_DB_OVERVIEW_SQL = text(
    """
    SELECT current_database() AS database_name,
           version() AS version_text,
           (SELECT version_num FROM public.alembic_version LIMIT 1) AS migration_version,
           pg_database_size(current_database()) AS size_bytes,
           current_setting('max_connections')::int AS max_connections,
           (SELECT count(*) FROM pg_stat_activity) AS connections,
           (SELECT count(*)
              FROM pg_class c
              JOIN pg_namespace n ON n.oid = c.relnamespace
             WHERE c.relkind = 'r'
               AND n.nspname !~ '^pg_'
               AND n.nspname <> 'information_schema') AS table_count,
           COALESCE((SELECT round(100.0 * blks_hit / NULLIF(blks_hit + blks_read, 0), 2)
                       FROM pg_stat_database
                      WHERE datname = current_database()), 0) AS cache_hit_percent
    """
)

_DB_TABLES_SQL = text(
    """
    SELECT n.nspname AS schema_name,
           c.relname AS table_name,
           COALESCE(s.n_live_tup, 0) AS est_rows,
           pg_total_relation_size(c.oid) AS total_bytes,
           (SELECT count(*)
              FROM pg_attribute a
             WHERE a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped) AS column_count,
           s.last_analyze
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
     WHERE c.relkind = 'r'
       AND n.nspname !~ '^pg_'
       AND n.nspname <> 'information_schema'
     ORDER BY total_bytes DESC, n.nspname, c.relname
    """
)

# schema / 表名一律参数绑定（`:schema_name` / `:table_name`），不拼接进 SQL
_DB_COLUMNS_SQL = text(
    """
    SELECT a.attnum AS ordinal,
           a.attname AS column_name,
           format_type(a.atttypid, a.atttypmod) AS data_type,
           NOT a.attnotnull AS nullable,
           pg_get_expr(d.adbin, d.adrelid) AS default_value,
           col_description(a.attrelid, a.attnum) AS comment
      FROM pg_attribute a
      JOIN pg_class c ON c.oid = a.attrelid
      JOIN pg_namespace n ON n.oid = c.relnamespace
      LEFT JOIN pg_attrdef d ON d.adrelid = a.attrelid AND d.adnum = a.attnum
     WHERE n.nspname = :schema_name AND c.relname = :table_name
       AND a.attnum > 0 AND NOT a.attisdropped
     ORDER BY a.attnum
    """
)

_DB_TABLE_META_SQL = text(
    """
    SELECT COALESCE(s.n_live_tup, 0) AS est_rows,
           pg_total_relation_size(c.oid) AS total_bytes
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
      LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
     WHERE n.nspname = :schema_name AND c.relname = :table_name AND c.relkind = 'r'
    """
)


async def get_db_tables() -> DbTablesData:
    """数据库概览 + 全部业务表清单（只读，不含数据内容）。"""
    async with engine.connect() as conn:
        overview = (await conn.execute(_DB_OVERVIEW_SQL)).mappings().one()
        rows = (await conn.execute(_DB_TABLES_SQL)).mappings().all()

    return DbTablesData(
        overview=DbOverview(
            database=overview["database_name"],
            version=str(overview["version_text"]).split(" on ")[0],
            migration_version=overview["migration_version"],
            size_bytes=int(overview["size_bytes"] or 0),
            table_count=int(overview["table_count"] or 0),
            connections=int(overview["connections"] or 0),
            max_connections=int(overview["max_connections"] or 0),
            cache_hit_percent=float(overview["cache_hit_percent"] or 0),
        ),
        items=[
            DbTableItem(
                schema=row["schema_name"],
                table=row["table_name"],
                est_rows=int(row["est_rows"] or 0),
                total_bytes=int(row["total_bytes"] or 0),
                column_count=int(row["column_count"] or 0),
                last_analyze=row["last_analyze"].isoformat() if row["last_analyze"] else None,
            )
            for row in rows
        ],
    )


async def get_db_table_columns(schema: str, table: str) -> DbColumnsData:
    """单表字段结构（列名 / 类型 / 可空 / 默认值 / 注释）。只读，不含数据内容。"""
    params = {"schema_name": schema, "table_name": table}
    async with engine.connect() as conn:
        meta = (await conn.execute(_DB_TABLE_META_SQL, params)).mappings().first()
        if meta is None:
            raise BadRequestException(f"表不存在：{schema}.{table}")

        rows = (await conn.execute(_DB_COLUMNS_SQL, params)).mappings().all()

    return DbColumnsData(
        schema=schema,
        table=table,
        est_rows=int(meta["est_rows"] or 0),
        total_bytes=int(meta["total_bytes"] or 0),
        items=[
            DbColumnItem(
                ordinal=int(row["ordinal"]),
                name=row["column_name"],
                data_type=row["data_type"],
                nullable=bool(row["nullable"]),
                default=row["default_value"],
                comment=row["comment"],
            )
            for row in rows
        ],
    )


# ── 工具 ──────────────────────────────────────────────────────────


def _elapsed_ms(start: float) -> int:
    return round((time.perf_counter() - start) * 1000)


def _uptime_seconds() -> int:
    return int((datetime.now(UTC) - _STARTED_AT).total_seconds())
