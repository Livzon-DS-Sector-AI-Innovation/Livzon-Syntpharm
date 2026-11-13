import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

type Schemas = components['schemas']

const P = (path: string) => `${getApiBaseUrl()}/api/v1/permission${path}`

function auth(token?: string): Record<string, string> | undefined {
  return token ? { Authorization: `Bearer ${token}` } : undefined
}

// ── 角色 ──────────────────────────────────────────────────────────

export function getRoles(token?: string) {
  return apiFetch<Schemas['RoleListResponse']>(P('/roles'), { headers: auth(token) })
}

export function createRole(data: Schemas['app__platform__permission__schemas__RoleCreate'], token?: string) {
  return apiFetch<Schemas['RoleDetailApiResponse']>(P('/roles'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function updateRole(
  id: string,
  data: Schemas['app__platform__permission__schemas__RoleUpdate'],
  token?: string,
) {
  return apiFetch<Schemas['RoleDetailApiResponse']>(P(`/roles/${id}`), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function deleteRole(id: string, token?: string) {
  return apiFetch<Schemas['app__platform__permission__schemas__MessageApiResponse']>(P(`/roles/${id}`), {
    method: 'DELETE',
    headers: auth(token),
  })
}

// ── 权限目录 ──────────────────────────────────────────────────────

export function getPermissions(token?: string) {
  return apiFetch<Schemas['PermissionListResponse']>(P('/permissions'), { headers: auth(token) })
}

export function getPermissionTree(token?: string) {
  return apiFetch<Schemas['PermissionTreeResponse']>(P('/tree'), { headers: auth(token) })
}

export function getApiBindings(token?: string) {
  return apiFetch<Schemas['ApiBindingListResponse']>(P('/api-bindings'), { headers: auth(token) })
}

/** 单个权限码绑定的接口清单（权限树按需展开用，权限口径 platform:role:read）。 */
export function getPermissionApiBindings(code: string, token?: string) {
  return apiFetch<Schemas['PermissionApiBindingListResponse']>(
    P(`/permissions/${encodeURIComponent(code)}/api-bindings`),
    { headers: auth(token) },
  )
}

// ── 授权 ──────────────────────────────────────────────────────────

export function getDepartments(token?: string) {
  return apiFetch<Schemas['DepartmentOptionListResponse']>(P('/departments'), { headers: auth(token) })
}

export function getPermissionPreview(userId: string, token?: string) {
  return apiFetch<Schemas['MyPermissionsResponse']>(P(`/preview/${userId}`), { headers: auth(token) })
}

export function getGrants(userId?: string, token?: string) {
  const q = userId ? `?user_id=${userId}` : ''
  return apiFetch<Schemas['GrantListResponse']>(P(`/grants${q}`), { headers: auth(token) })
}

export function createGrant(data: Schemas['GrantCreate'], token?: string) {
  return apiFetch<Schemas['GrantDetailApiResponse']>(P('/grants'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function updateGrant(id: string, data: Schemas['GrantUpdate'], token?: string) {
  return apiFetch<Schemas['GrantDetailApiResponse']>(P(`/grants/${id}`), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function deleteGrant(id: string, token?: string) {
  return apiFetch<Schemas['app__platform__permission__schemas__MessageApiResponse']>(P(`/grants/${id}`), {
    method: 'DELETE',
    headers: auth(token),
  })
}

// ── 批量操作 ───────────────────────────────────────────────────────

export function batchUpdateRoleStatus(data: Schemas['StatusBatchRequest'], token?: string) {
  return apiFetch<Schemas['app__platform__permission__schemas__BatchResultApiResponse']>(P('/roles/batch-status'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function batchDeleteRoles(data: Schemas['IdsBatchRequest'], token?: string) {
  return apiFetch<Schemas['app__platform__permission__schemas__BatchResultApiResponse']>(P('/roles/batch-delete'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function batchUpdateGrantStatus(data: Schemas['StatusBatchRequest'], token?: string) {
  return apiFetch<Schemas['app__platform__permission__schemas__BatchResultApiResponse']>(P('/grants/batch-status'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export function batchDeleteGrants(data: Schemas['IdsBatchRequest'], token?: string) {
  return apiFetch<Schemas['app__platform__permission__schemas__BatchResultApiResponse']>(P('/grants/batch-delete'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

// ── 当前用户权限 ──────────────────────────────────────────────────

export function getMyPermissions(token?: string) {
  return apiFetch<Schemas['MyPermissionsResponse']>(P('/my-permissions'), { headers: auth(token) })
}
