import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function getUsers(params?: { keyword?: string; status?: string }, token?: string) {
  const search = new URLSearchParams()
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.status) search.set('status', params.status)
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