"""系统运维 API 的响应模型（完整信封，符合 AGENTS.md）。

只读为主，唯一写操作是「按前缀清理 Redis 缓存」。
"""

from pydantic import BaseModel, Field

# ── 服务健康 ──────────────────────────────────────────────────────


class ComponentHealth(BaseModel):
    name: str = Field(..., description="组件名")
    status: str = Field(..., description="ok / error / disabled")
    latency_ms: int | None = Field(None, description="探测耗时（毫秒）")
    uptime_seconds: int | None = Field(None, description="运行时长（秒），取不到为 null")
    detail: str | None = Field(None, description="失败原因或补充说明")


class HealthResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[ComponentHealth]


# ── 系统信息 ──────────────────────────────────────────────────────


class DependencyInfo(BaseModel):
    name: str
    version: str


class SystemInfoData(BaseModel):
    app_name: str
    app_env: str
    version: str
    python_version: str
    started_at: str
    uptime_seconds: int
    dependencies: list[DependencyInfo]


class SystemInfoResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: SystemInfoData


# ── 资源监控 ──────────────────────────────────────────────────────


class DiskUsage(BaseModel):
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent: float


class MemoryUsage(BaseModel):
    total_gb: float
    used_gb: float
    available_gb: float
    percent: float


class LoadAverage(BaseModel):
    load1: float
    load5: float
    load15: float
    cpu_count: int


class ResourcesData(BaseModel):
    disk: DiskUsage
    memory: MemoryUsage
    load: LoadAverage


class ResourcesResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: ResourcesData


# ── Redis ─────────────────────────────────────────────────────────


class RedisOverviewData(BaseModel):
    dbsize: int
    used_memory_human: str
    connected_clients: int
    keyspace_hits: int
    keyspace_misses: int
    uptime_in_days: int
    version: str


class RedisOverviewResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: RedisOverviewData


class RedisKeysData(BaseModel):
    keys: list[str]
    total_scanned: int
    truncated: bool


class RedisKeysResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: RedisKeysData


class RedisDeleteResult(BaseModel):
    deleted: int
    pattern: str


class RedisDeleteResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: RedisDeleteResult


# ── 定时任务 / 后台任务清单 ───────────────────────────────────────


class ScheduledTaskItem(BaseModel):
    name: str = Field(..., description="任务名")
    kind: str = Field(..., description="task / generator / worker / loop")
    schedule: str = Field("", description="调度描述，如 cron 0 2 * * *")
    module: str = Field("", description="所属模块")
    enabled: bool = True
    description: str = ""


class ScheduledTasksResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[ScheduledTaskItem]


class TaskToggleRequest(BaseModel):
    enabled: bool = Field(..., description="目标状态：true 启用 / false 禁用")


class TaskToggleResult(BaseModel):
    name: str
    enabled: bool


class TaskToggleResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: TaskToggleResult


# ── API 启停开关 ──────────────────────────────────────────────────


class ApiRouteItemModel(BaseModel):
    method: str
    route: str
    summary: str = ""
    tags: list[str] = Field(default_factory=list)
    disabled: bool = False
    reason: str | None = None
    protected: bool = Field(False, description="保护名单内（不可禁用）")


class ApiRoutesResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: list[ApiRouteItemModel]


class ApiSwitchRequest(BaseModel):
    method: str = Field(..., min_length=1, max_length=16)
    route: str = Field(..., min_length=1, max_length=256)
    enabled: bool
    reason: str | None = Field(None, max_length=500)


class ApiSwitchResult(BaseModel):
    method: str
    route: str
    enabled: bool
    message: str


class ApiSwitchResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: ApiSwitchResult


# ── 日志管理 ──────────────────────────────────────────────────────


class LogItemModel(BaseModel):
    seq: int
    timestamp: str
    level: str
    logger: str
    message: str
    request_id: str = "-"


class LogsData(BaseModel):
    items: list[LogItemModel]
    total: int
    buffer_size: int


class LogsResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: LogsData


class LogClearResult(BaseModel):
    cleared: int


class LogsClearResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: LogClearResult


# ── 数据库信息（只读：结构 / 体积 / 行数估算） ─────────────────────
#
# 红线：这里**只暴露结构**（表名、行数估算、体积、列名、类型、注释），
# 绝不返回任何一行的数据内容。


class DbOverview(BaseModel):
    """数据库概览。"""

    database: str
    version: str = Field(..., description="数据库版本（已裁掉 OS 后缀）")
    migration_version: str | None = Field(None, description="当前 Alembic 迁移版本号（alembic_version.version_num）")
    size_bytes: int = Field(..., description="当前库占用字节数")
    table_count: int = Field(..., description="业务表数量（排除 pg_* 系统 schema）")
    connections: int = Field(..., description="当前连接数")
    max_connections: int = Field(..., description="最大连接数")
    cache_hit_percent: float = Field(..., description="缓存命中率（%），越高越好")


class DbTableItem(BaseModel):
    """一张业务表的元信息（不含数据内容）。"""

    schema: str  # type: ignore[assignment]  # 字段名与 BaseModel.schema 方法同名
    table: str
    est_rows: int = Field(..., description="估算行数（统计收集器，ANALYZE 后准确）")
    total_bytes: int = Field(..., description="表 + 索引占用字节数")
    column_count: int
    last_analyze: str | None = Field(None, description="最后一次 ANALYZE 时间；null = 从未分析")


class DbTablesData(BaseModel):
    overview: DbOverview
    items: list[DbTableItem]


class DbTablesResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DbTablesData


class DbColumnItem(BaseModel):
    """一个字段的结构定义（不含数据内容）。"""

    ordinal: int
    name: str
    data_type: str = Field(..., description="完整类型，如 character varying(255)")
    nullable: bool
    default: str | None = None
    comment: str | None = None


class DbColumnsData(BaseModel):
    schema: str  # type: ignore[assignment]  # 字段名与 BaseModel.schema 方法同名
    table: str
    est_rows: int
    total_bytes: int
    items: list[DbColumnItem]


class DbColumnsResponse(BaseModel):
    code: int = 200
    message: str = "success"
    data: DbColumnsData
