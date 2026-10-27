import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

type Schemas = components['schemas']

const P = (path: string) => `${getApiBaseUrl()}/api/v1/system${path}`

function auth(token?: string): Record<string, string> | undefined {
  return token ? { Authorization: `Bearer ${token}` } : undefined
}

export function getHealth(token?: string) {
  return apiFetch<Schemas['HealthResponse']>(P('/health'), { headers: auth(token) })
}

export function getSystemInfo(token?: string) {
  return apiFetch<Schemas['SystemInfoResponse']>(P('/info'), { headers: auth(token) })
}

export function getResources(token?: string) {
  return apiFetch<Schemas['ResourcesResponse']>(P('/resources'), { headers: auth(token) })
}

export function getRedisOverview(token?: string) {
  return apiFetch<Schemas['RedisOverviewResponse']>(P('/redis'), { headers: auth(token) })
}

export function getRedisKeys(prefix: string, limit = 200, token?: string) {
  const params = new URLSearchParams()
  if (prefix) params.set('prefix', prefix)
  params.set('limit', String(limit))
  return apiFetch<Schemas['RedisKeysResponse']>(P(`/redis/keys?${params.toString()}`), { headers: auth(token) })
}

export function deleteRedisKeys(prefix: string, token?: string) {
  const params = new URLSearchParams({ prefix })
  return apiFetch<Schemas['RedisDeleteResponse']>(P(`/redis/keys?${params.toString()}`), {
    method: 'DELETE',
    headers: auth(token),
  })
}

export function getScheduledTasks(token?: string) {
  return apiFetch<Schemas['ScheduledTasksResponse']>(P('/scheduled-tasks'), { headers: auth(token) })
}

export function toggleScheduledTask(name: string, enabled: boolean, token?: string) {
  return apiFetch<Schemas['TaskToggleResponse']>(P(`/scheduled-tasks/${encodeURIComponent(name)}/toggle`), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify({ enabled } satisfies Schemas['TaskToggleRequest']),
  })
}

export function getApiRoutes(token?: string) {
  return apiFetch<Schemas['ApiRoutesResponse']>(P('/api-routes'), { headers: auth(token) })
}

// ── 批量操作 ───────────────────────────────────────────────────────

export function batchToggleScheduledTasks(data: Schemas['TaskBatchToggleRequest'], token?: string) {
  return apiFetch<Schemas['BatchResultResponse']>(P('/scheduled-tasks/batch-toggle'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function batchSetApiSwitch(data: Schemas['ApiSwitchBatchRequest'], token?: string) {
  return apiFetch<Schemas['BatchResultResponse']>(P('/api-routes/batch-switch'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function setApiSwitch(data: Schemas['ApiSwitchRequest'], token?: string) {
  return apiFetch<Schemas['ApiSwitchResponse']>(P('/api-routes/switch'), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function getLogs(level: string, keyword: string, limit = 500, token?: string) {
  const params = new URLSearchParams()
  if (level) params.set('level', level)
  if (keyword) params.set('keyword', keyword)
  params.set('limit', String(limit))
  return apiFetch<Schemas['LogsResponse']>(P(`/logs?${params.toString()}`), { headers: auth(token) })
}

export function clearLogs(token?: string) {
  return apiFetch<Schemas['LogsClearResponse']>(P('/logs'), { method: 'DELETE', headers: auth(token) })
}

export function getDbTables(token?: string) {
  return apiFetch<Schemas['DbTablesResponse']>(P('/db/tables'), { headers: auth(token) })
}

export function getDbTableColumns(schema: string, table: string, token?: string) {
  const s = encodeURIComponent(schema)
  const t = encodeURIComponent(table)
  return apiFetch<Schemas['DbColumnsResponse']>(P(`/db/tables/${s}/${t}/columns`), { headers: auth(token) })
}
