/**
 * 系统运维 UI 类型（对应后端 platform/system 运维 API）。
 */

export interface ComponentHealth {
  name: string
  status: 'ok' | 'error' | 'disabled' | string
  latency_ms: number | null
  /** 运行时长（秒）；取不到为 null（如 minio） */
  uptime_seconds: number | null
  detail: string | null
}

export interface DependencyInfo {
  name: string
  version: string
}

export interface SystemInfoData {
  app_name: string
  app_env: string
  version: string
  python_version: string
  started_at: string
  uptime_seconds: number
  dependencies: DependencyInfo[]
}

export interface DiskUsage {
  path: string
  total_gb: number
  used_gb: number
  free_gb: number
  percent: number
}

export interface MemoryUsage {
  total_gb: number
  used_gb: number
  available_gb: number
  percent: number
}

export interface LoadAverage {
  load1: number
  load5: number
  load15: number
  cpu_count: number
}

export interface ResourcesData {
  disk: DiskUsage
  memory: MemoryUsage
  load: LoadAverage
}

export interface RedisOverviewData {
  dbsize: number
  used_memory_human: string
  connected_clients: number
  keyspace_hits: number
  keyspace_misses: number
  uptime_in_days: number
  version: string
}

export interface RedisKeysData {
  keys: string[]
  total_scanned: number
  truncated: boolean
}

export interface RedisDeleteResult {
  deleted: number
  pattern: string
}

export interface ScheduledTaskItem {
  name: string
  kind: 'task' | 'generator' | 'worker' | 'loop' | string
  schedule: string
  module: string
  enabled: boolean
  description: string
}

export interface ApiRouteItem {
  method: string
  route: string
  summary: string
  tags: string[]
  disabled: boolean
  reason: string | null
  protected: boolean
}

export interface ApiSwitchResult {
  method: string
  route: string
  enabled: boolean
  message: string
}

export interface LogItem {
  seq: number
  timestamp: string
  level: string
  logger: string
  message: string
  request_id: string
}

export interface LogsData {
  items: LogItem[]
  total: number
  buffer_size: number
}

export interface LogClearResult {
  cleared: number
}

// ── 数据库信息（只读：结构 / 体积 / 行数估算；不含任何数据内容） ─────

export interface DbOverview {
  database: string
  version: string
  size_bytes: number
  table_count: number
  connections: number
  max_connections: number
  cache_hit_percent: number
}

export interface DbTableItem {
  schema: string
  table: string
  /** 估算行数（统计收集器，ANALYZE 后准确） */
  est_rows: number
  total_bytes: number
  column_count: number
  last_analyze: string | null
}

export interface DbTablesData {
  overview: DbOverview
  items: DbTableItem[]
}

export interface DbColumnItem {
  ordinal: number
  name: string
  data_type: string
  nullable: boolean
  default: string | null
  comment: string | null
}

export interface DbColumnsData {
  schema: string
  table: string
  est_rows: number
  total_bytes: number
  items: DbColumnItem[]
}
