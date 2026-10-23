import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'
import type {
  ChangePasswordRequest,
  LocalUserCreate,
  PasswordResetRequest,
  UserBatchStatusRequest,
  UserManagementUpdate,
} from '@/types/users'

type Schemas = components['schemas']

const U = (path: string) => `${getApiBaseUrl()}/api/v1/identity${path}`

function auth(token?: string): Record<string, string> | undefined {
  return token ? { Authorization: `Bearer ${token}` } : undefined
}

export interface UserListQuery {
  keyword?: string
  status?: string
  auth_source?: string
  unbound_only?: boolean
  must_change_password?: boolean
  limit?: number
}

export async function getUsers(params?: UserListQuery, token?: string) {
  const search = new URLSearchParams()
  if (params?.keyword) search.set('keyword', params.keyword)
  if (params?.status) search.set('status', params.status)
  if (params?.auth_source) search.set('auth_source', params.auth_source)
  if (params?.unbound_only) search.set('unbound_only', 'true')
  if (params?.must_change_password !== undefined) {
    search.set('must_change_password', String(params.must_change_password))
  }
  if (params?.limit) search.set('limit', String(params.limit))
  const query = search.toString()
  return apiFetch<Schemas['UserManagementListApiResponse']>(U(`/users${query ? `?${query}` : ''}`), {
    headers: auth(token),
  })
}

export async function createUser(data: LocalUserCreate, token?: string) {
  return apiFetch<Schemas['UserCreateApiResponse']>(U('/users'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export async function updateUser(id: string, data: UserManagementUpdate, token?: string) {
  return apiFetch<Schemas['UserManagementApiResponse']>(U(`/users/${id}`), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export async function batchUpdateUserStatus(data: UserBatchStatusRequest, token?: string) {
  return apiFetch<Schemas['UserBatchStatusApiResponse']>(U('/users/batch-status'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export async function resetUserPassword(id: string, data: PasswordResetRequest, token?: string) {
  return apiFetch<Schemas['PasswordResetApiResponse']>(U(`/users/${id}/reset-password`), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

export async function changeMyPassword(data: ChangePasswordRequest, token?: string) {
  return apiFetch<Schemas['ChangePasswordApiResponse']>(U('/me/password'), {
    method: 'POST',
    headers: auth(token),
    body: JSON.stringify(data),
  })
}

/** 删除账号（后端限定仅超级管理员可调用）。 */
export async function deleteUser(id: string, token?: string) {
  return apiFetch<Schemas['UserDeleteApiResponse']>(U(`/users/${id}`), {
    method: 'DELETE',
    headers: auth(token),
  })
}

export async function unbindFeishuUser(id: string, token?: string) {
  return apiFetch<Schemas['UserUnbindFeishuApiResponse']>(U(`/users/${id}/bind-feishu`), {
    method: 'DELETE',
    headers: auth(token),
  })
}

export async function revokeUserSessions(id: string, token?: string) {
  return apiFetch<Schemas['SessionRevokeApiResponse']>(U(`/users/${id}/sessions`), {
    method: 'DELETE',
    headers: auth(token),
  })
}

export async function listSessions(token?: string) {
  return apiFetch<Schemas['SessionListApiResponse']>(U('/sessions'), { headers: auth(token) })
}

export async function revokeSession(jti: string, token?: string) {
  return apiFetch<Schemas['SessionRevokeApiResponse']>(U(`/sessions/${jti}`), {
    method: 'DELETE',
    headers: auth(token),
  })
}
