/**
 * 系统运维类型。
 *
 * 全部从 `@/types/generated/schema` 派生（对应后端 platform/system 运维 API 的 response_model）。
 */
import type { components } from '@/types/generated/schema'

export type ComponentHealth = components['schemas']['ComponentHealth']
export type DependencyInfo = components['schemas']['DependencyInfo']
export type SystemInfoData = components['schemas']['SystemInfoData']
export type DiskUsage = components['schemas']['DiskUsage']
export type MemoryUsage = components['schemas']['MemoryUsage']
export type LoadAverage = components['schemas']['LoadAverage']
export type ResourcesData = components['schemas']['ResourcesData']

export type RedisOverviewData = components['schemas']['RedisOverviewData']
export type RedisKeysData = components['schemas']['RedisKeysData']
export type RedisDeleteResult = components['schemas']['RedisDeleteResult']

export type ScheduledTaskItem = components['schemas']['ScheduledTaskItem']
export type ApiRouteItem = components['schemas']['ApiRouteItemModel']
export type ApiSwitchResult = components['schemas']['ApiSwitchResult']

export type BatchFailureItem = components['schemas']['BatchFailure']

/** 批量操作结果：后端 schema 给 succeeded/failed 设了默认值，OpenAPI 标成可选；
 *  实际响应总会返回这两个数组，这里恢复成必填，避免消费端冗余判空。 */
export type BatchResult = {
  succeeded: NonNullable<components['schemas']['BatchResultData']['succeeded']>
  failed: NonNullable<components['schemas']['BatchResultData']['failed']>
}

export type LogItem = components['schemas']['LogItemModel']
export type LogsData = components['schemas']['LogsData']
export type LogClearResult = components['schemas']['LogClearResult']

// ── 数据库信息（只读：结构 / 体积 / 行数估算；不含任何数据内容） ─────

export type DbOverview = components['schemas']['DbOverview']
export type DbTableItem = components['schemas']['DbTableItem']
export type DbTablesData = components['schemas']['DbTablesData']
export type DbColumnItem = components['schemas']['DbColumnItem']
export type DbColumnsData = components['schemas']['DbColumnsData']
