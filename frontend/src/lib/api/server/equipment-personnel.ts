import { apiFetch, getApiBaseUrl } from './base'
import type { components } from '@/types/generated/schema'

const BASE = `${getApiBaseUrl()}/api/v1/equipment/personnel`

export async function createRoleApi(data: components['schemas']['RoleCreate'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/roles`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function updateRoleApi(id: string, data: components['schemas']['RoleUpdate'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/roles/${id}`, { method: 'PUT', body: JSON.stringify(data), headers })
}

export async function deleteRoleApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/roles/${id}`, { method: 'DELETE', headers })
}

export async function addPersonnelApi(data: components['schemas']['PersonnelAddRequest'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function deletePersonnelApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/${id}`, { method: 'DELETE', headers })
}

export async function assignRolesApi(personnelId: string, data: components['schemas']['PersonnelRoleAssign'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/${personnelId}/roles`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function assignCategoriesApi(personnelId: string, data: components['schemas']['PersonnelCategoryAssign'], headers?: Record<string, string>) {
  return apiFetch(`${BASE}/${personnelId}/categories`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function refreshFeishuApi(headers?: Record<string, string>) {
  return apiFetch(`${BASE}/refresh-feishu`, { method: 'POST', headers })
}
