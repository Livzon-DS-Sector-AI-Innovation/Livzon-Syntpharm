import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

const P = (path: string) => `${getApiBaseUrl()}/api/v1/permission${path}`
const ID = (path: string) => `${getApiBaseUrl()}/api/v1/identity${path}`

function auth(token?: string): Record<string, string> | undefined {
  return token ? { Authorization: `Bearer ${token}` } : undefined
}

// ── 角色 ──────────────────────────────────────────────────────────

export function getRoles(token?: string) {
  return apiFetch(P('/roles'), { headers: auth(token) })
}

export function createRole(data: unknown, token?: string) {
  return apiFetch(P('/roles'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function updateRole(id: string, data: unknown, token?: string) {
  return apiFetch(P(`/roles/${id}`), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function deleteRole(id: string, token?: string) {
  return apiFetch(P(`/roles/${id}`), { method: 'DELETE', headers: auth(token) })
}

// ── 权限目录 ──────────────────────────────────────────────────────

export function getPermissions(token?: string) {
  return apiFetch(P('/permissions'), { headers: auth(token) })
}

export function getPermissionTree(token?: string) {
  return apiFetch(P('/tree'), { headers: auth(token) })
}

export function getApiBindings(token?: string) {
  return apiFetch(P('/api-bindings'), { headers: auth(token) })
}

// ── 授权 ──────────────────────────────────────────────────────────

export function getDepartments(token?: string) {
  return apiFetch(P('/departments'), { headers: auth(token) })
}

export function getGrants(userId?: string, token?: string) {
  const q = userId ? `?user_id=${userId}` : ''
  return apiFetch(P(`/grants${q}`), { headers: auth(token) })
}

export function createGrant(data: unknown, token?: string) {
  return apiFetch(P('/grants'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function updateGrant(id: string, data: unknown, token?: string) {
  return apiFetch(P(`/grants/${id}`), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function deleteGrant(id: string, token?: string) {
  return apiFetch(P(`/grants/${id}`), { method: 'DELETE', headers: auth(token) })
}

// ── 用户选择列表（授权下拉用）─────────────────────────────────────

export function getUsersForSelect(token?: string) {
  // 后端 limit 上限为 100（identity/api.py 的 Query(20, ge=1, le=100)），超过会 422
  return apiFetch(ID('/users?limit=100'), { headers: auth(token) })
}

// ── 当前用户权限 ──────────────────────────────────────────────────

export function getMyPermissions(token?: string) {
  return apiFetch(P('/my-permissions'), { headers: auth(token) })
}
