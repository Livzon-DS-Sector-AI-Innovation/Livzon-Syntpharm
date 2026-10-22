/**
 * 系统运维类型。
 *
 * 已有 response_model 的运维端点（组件健康/系统信息/资源使用）从 `@/types/generated/schema`
 * 派生；Redis/日志/数据库/调度/API 开关等端点尚未补充 response_model（OpenAPI 未生成对应
 * schema），暂保留手写，待后端补齐后再迁移。
 */
import type { components } from '@/types/generated/schema'

export type ComponentHealth = components['schemas']['ComponentHealth']
export type DependencyInfo = components['schemas']['DependencyInfo']
export type SystemInfoData = components['schemas']['SystemInfoData']
export type DiskUsage = components['schemas']['DiskUsage']
export type MemoryUsage = components['schemas']['MemoryUsage']
export type LoadAverage = components['schemas']['LoadAverage']
export type ResourcesData = components['schemas']['ResourcesData']

// ── 以下运维端点尚无 response_model，暂保留手写（待后端补齐后迁移） ──

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

/** 批量操作失败项（后端统一结构）。 */
export interface BatchFailureItem {
  key: string
  label?: string | null
  reason: string
}

/** 批量操作结果：成功标识列表 + 失败明细。 */
export interface BatchResult {
  succeeded: string[]
  failed: BatchFailureItem[]
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
  migration_version: string | null
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
