import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

const P = (path: string) => `${getApiBaseUrl()}/api/v1/system${path}`

function auth(token?: string): Record<string, string> | undefined {
  return token ? { Authorization: `Bearer ${token}` } : undefined
}

export function getHealth(token?: string) {
  return apiFetch(P('/health'), { headers: auth(token) })
}

export function getSystemInfo(token?: string) {
  return apiFetch(P('/info'), { headers: auth(token) })
}

export function getResources(token?: string) {
  return apiFetch(P('/resources'), { headers: auth(token) })
}

export function getRedisOverview(token?: string) {
  return apiFetch(P('/redis'), { headers: auth(token) })
}

export function getRedisKeys(prefix: string, limit = 200, token?: string) {
  const params = new URLSearchParams()
  if (prefix) params.set('prefix', prefix)
  params.set('limit', String(limit))
  return apiFetch(P(`/redis/keys?${params.toString()}`), { headers: auth(token) })
}

export function deleteRedisKeys(prefix: string, token?: string) {
  const params = new URLSearchParams({ prefix })
  return apiFetch(P(`/redis/keys?${params.toString()}`), {
    method: 'DELETE',
    headers: auth(token),
  })
}

export function getScheduledTasks(token?: string) {
  return apiFetch(P('/scheduled-tasks'), { headers: auth(token) })
}

export function getApiRoutes(token?: string) {
  return apiFetch(P('/api-routes'), { headers: auth(token) })
}

export function setApiSwitch(
  method: string,
  route: string,
  enabled: boolean,
  reason: string | null,
  token?: string,
) {
  return apiFetch(P('/api-routes/switch'), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify({ method, route, enabled, reason }),
  })
}

export function getLogs(level: string, keyword: string, limit = 500, token?: string) {
  const params = new URLSearchParams()
  if (level) params.set('level', level)
  if (keyword) params.set('keyword', keyword)
  params.set('limit', String(limit))
  return apiFetch(P(`/logs?${params.toString()}`), { headers: auth(token) })
}

export function clearLogs(token?: string) {
  return apiFetch(P('/logs'), { method: 'DELETE', headers: auth(token) })
}

export function getDbTables(token?: string) {
  return apiFetch(P('/db/tables'), { headers: auth(token) })
}

export function getDbTableColumns(schema: string, table: string, token?: string) {
  const s = encodeURIComponent(schema)
  const t = encodeURIComponent(table)
  return apiFetch(P(`/db/tables/${s}/${t}/columns`), { headers: auth(token) })
}
