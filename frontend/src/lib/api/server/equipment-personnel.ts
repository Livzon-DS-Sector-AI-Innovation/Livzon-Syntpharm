import { apiFetch, getApiBaseUrl } from './base'

const BASE = `${getApiBaseUrl()}/api/v1/equipment/personnel`

export async function createRoleApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/roles`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function updateRoleApi(id: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/roles/${id}`, { method: 'PUT', body: JSON.stringify(data), headers })
}

export async function deleteRoleApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/roles/${id}`, { method: 'DELETE', headers })
}

export async function addPersonnelApi(data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function deletePersonnelApi(id: string, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/${id}`, { method: 'DELETE', headers })
}

export async function assignRolesApi(personnelId: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/${personnelId}/roles`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function assignCategoriesApi(personnelId: string, data: any, headers?: Record<string, string>) {
  return apiFetch(`${BASE}/${personnelId}/categories`, { method: 'POST', body: JSON.stringify(data), headers })
}

export async function refreshFeishuApi(headers?: Record<string, string>) {
  return apiFetch(`${BASE}/refresh-feishu`, { method: 'POST', headers })
}
