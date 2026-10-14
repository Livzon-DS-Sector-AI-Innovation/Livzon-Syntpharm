'use server'

import { cookies } from 'next/headers'
import {
  clearLogs as clearLogsApi,
  deleteRedisKeys as deleteRedisKeysApi,
  getApiRoutes as getApiRoutesApi,
  getDbTableColumns as getDbTableColumnsApi,
  getDbTables as getDbTablesApi,
  getHealth,
  getLogs as getLogsApi,
  getRedisKeys as getRedisKeysApi,
  getRedisOverview,
  getResources,
  getScheduledTasks,
  getSystemInfo,
  setApiSwitch as setApiSwitchApi,
} from '@/lib/api/server/system-ops'
import type {
  ApiRouteItem,
  ApiSwitchResult,
  ComponentHealth,
  DbColumnsData,
  DbTablesData,
  LogClearResult,
  LogsData,
  RedisDeleteResult,
  RedisKeysData,
  RedisOverviewData,
  ResourcesData,
  ScheduledTaskItem,
  SystemInfoData,
} from '@/types/system-ops'

async function getAuthToken(): Promise<string | undefined> {
  const cookieStore = await cookies()
  return cookieStore.get('auth_token')?.value
}

export async function fetchHealth(): Promise<ComponentHealth[]> {
  const token = await getAuthToken()
  const res = (await getHealth(token)) as { data: ComponentHealth[] }
  return res.data ?? []
}

export async function fetchSystemInfo(): Promise<SystemInfoData | null> {
  const token = await getAuthToken()
  const res = (await getSystemInfo(token)) as { data: SystemInfoData }
  return res.data ?? null
}

export async function fetchResources(): Promise<ResourcesData | null> {
  const token = await getAuthToken()
  const res = (await getResources(token)) as { data: ResourcesData }
  return res.data ?? null
}

export async function fetchRedisOverview(): Promise<RedisOverviewData | null> {
  const token = await getAuthToken()
  const res = (await getRedisOverview(token)) as { data: RedisOverviewData }
  return res.data ?? null
}

export async function fetchRedisKeys(prefix: string): Promise<RedisKeysData> {
  const token = await getAuthToken()
  const res = (await getRedisKeysApi(prefix, 200, token)) as { data: RedisKeysData }
  return res.data ?? { keys: [], total_scanned: 0, truncated: false }
}

export async function deleteRedisKeys(prefix: string): Promise<RedisDeleteResult> {
  const token = await getAuthToken()
  const res = (await deleteRedisKeysApi(prefix, token)) as { data: RedisDeleteResult }
  return res.data
}

export async function fetchScheduledTasks(): Promise<ScheduledTaskItem[]> {
  const token = await getAuthToken()
  const res = (await getScheduledTasks(token)) as { data: ScheduledTaskItem[] }
  return res.data ?? []
}

export async function fetchApiRoutes(): Promise<ApiRouteItem[]> {
  const token = await getAuthToken()
  const res = (await getApiRoutesApi(token)) as { data: ApiRouteItem[] }
  return res.data ?? []
}

export async function setApiSwitch(
  method: string,
  route: string,
  enabled: boolean,
  reason: string | null,
): Promise<ApiSwitchResult> {
  const token = await getAuthToken()
  const res = (await setApiSwitchApi(method, route, enabled, reason, token)) as {
    data: ApiSwitchResult
  }
  return res.data
}

export async function fetchLogs(level = '', keyword = ''): Promise<LogsData> {
  const token = await getAuthToken()
  const res = (await getLogsApi(level, keyword, 500, token)) as { data: LogsData }
  return res.data ?? { items: [], total: 0, buffer_size: 0 }
}

export async function clearLogs(): Promise<LogClearResult> {
  const token = await getAuthToken()
  const res = (await clearLogsApi(token)) as { data: LogClearResult }
  return res.data
}

/** 数据库概览 + 业务表清单（只读，不含数据内容）。 */
export async function fetchDbTables(): Promise<DbTablesData | null> {
  const token = await getAuthToken()
  const res = (await getDbTablesApi(token)) as { data: DbTablesData }
  return res.data ?? null
}

/** 单表字段结构（只读，不含数据内容）。 */
export async function fetchDbTableColumns(
  schema: string,
  table: string,
): Promise<DbColumnsData | null> {
  const token = await getAuthToken()
  const res = (await getDbTableColumnsApi(schema, table, token)) as { data: DbColumnsData }
  return res.data ?? null
}
