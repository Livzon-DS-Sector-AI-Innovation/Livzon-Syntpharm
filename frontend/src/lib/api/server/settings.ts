import { apiFetch, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'
import type { components } from '@/types/generated/schema'

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

/**
 * 飞书（Livzon 助手）配置相关接口统一返回 `{code, message, data}` 信封，
 * 而组件期望直接拿到 `data`（FeishuConfig / FeishuDiagnosticResult / 同步结果）。
 * 这里统一解包，避免把信封当数据用——曾因此导致配置回显全空、
 * 「诊断权限」无论成败都提示「诊断失败」。
 */
async function fetchFeishuConfigData<T>(url: string, options: RequestInit): Promise<T> {
  const envelope = await apiFetch<{ code: number; data: T; message?: string }>(url, options)
  return unwrapResponse(envelope)
}

export async function getLivzonFeishuConfig(token?: string) {
  return fetchFeishuConfigData(`${getApiBaseUrl()}/api/v1/identity/feishu-config`, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  })
}

export async function saveLivzonFeishuConfig(data: unknown, token?: string) {
  return fetchFeishuConfigData(`${getApiBaseUrl()}/api/v1/identity/feishu-config`, {
    method: 'PUT',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function testLivzonFeishuConfig(data: unknown, token?: string) {
  return fetchFeishuConfigData(`${getApiBaseUrl()}/api/v1/identity/feishu-config/test`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data || null),
  })
}

export async function syncLivzonFeishuContacts(token?: string) {
  const envelope = await apiFetch<components['schemas']['SyncAllTriggerApiResponse']>(
    `${getApiBaseUrl()}/api/v1/identity/sync/all`,
    {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    },
  )
  return unwrapResponse(envelope)
}
