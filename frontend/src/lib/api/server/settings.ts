import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function getLLMConfigs(configType?: string, token?: string) {
  const searchParams = new URLSearchParams()
  if (configType) searchParams.set('config_type', configType)
  const queryString = searchParams.toString()
  const endpoint = `/llm/configs${queryString ? `?${queryString}` : ''}`
  return apiFetch(`${getApiBaseUrl()}/api/v1${endpoint}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

export async function getLLMConfig(id: string, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/llm/configs/${id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

export async function createLLMConfig(data: unknown, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/llm/configs`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function updateLLMConfig(id: string, data: unknown, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/llm/configs/${id}`, {
    method: 'PUT',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function deleteLLMConfig(id: string, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/llm/configs/${id}`, {
    method: 'DELETE',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

export async function testLLMConnection(token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/llm/configs/test`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

export async function getLivzonFeishuConfig(token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/feishu-config`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

export async function saveLivzonFeishuConfig(data: unknown, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/feishu-config`, {
    method: 'PUT',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function testLivzonFeishuConfig(data: unknown, token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/feishu-config/test`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data || null),
  })
}

export async function syncLivzonFeishuContacts(token?: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/identity/sync/all`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}