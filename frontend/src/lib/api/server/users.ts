import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function getUsers(
  params?: {
    keyword?: string
    status?: string
    auth_source?: string
    unbound_only?: boolean
    limit?: number
  },
  token?: string,
) {
  const search = new URLSearchParams()
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.status) search.set('status', params.status)
  if (params?.auth_source) search.set('auth_source', params.auth_source)
  if (params?.unbound_only) search.set('unbound_only', 'true')
  if (params?.limit) search.set('limit', String(params.limit))
  const query = search.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/users${query ? `?${query}` : ''}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

export async function createUser(data: unknown, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/users`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function updateUser(id: string, data: unknown, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/users/${id}`, {
    method: 'PUT',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function resetUserPassword(id: string, data: unknown, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/users/${id}/reset-password`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function bindFeishuUser(id: string, data: unknown, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/users/${id}/bind-feishu`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function unbindFeishuUser(id: string, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/users/${id}/bind-feishu`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}