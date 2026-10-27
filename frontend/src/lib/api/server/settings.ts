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

export async function createLLMConfig(
  data: components['schemas']['LLMConfigCreate'],
  token?: string,
) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/llm/configs`, {
    method: 'POST',
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
    body: JSON.stringify(data),
  })
}

export async function updateLLMConfig(
  id: string,
  data: components['schemas']['LLMConfigUpdate'],
  token?: string,
) {
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

// 飞书（Livzon 助手）配置：接口返回 `{code, message, data}` 信封，这里按生成 schema
// 标注信封类型并统一解包，避免把信封当数据用（曾导致配置回显全空、诊断恒失败）。

export async function getLivzonFeishuConfig(token?: string) {
  const envelope = await apiFetch<components['schemas']['FeishuConfigApiResponse']>(
    `${getApiBaseUrl()}/api/v1/identity/feishu-config`,
    { headers: token ? { Authorization: `Bearer ${token}` } : undefined },
  )
  return unwrapResponse(envelope)
}

export async function saveLivzonFeishuConfig(
  data: components['schemas']['FeishuConfigUpsert'],
  token?: string,
) {
  const envelope = await apiFetch<components['schemas']['FeishuConfigApiResponse']>(
    `${getApiBaseUrl()}/api/v1/identity/feishu-config`,
    {
      method: 'PUT',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: JSON.stringify(data),
    },
  )
  return unwrapResponse(envelope)
}

export async function testLivzonFeishuConfig(
  data: components['schemas']['FeishuConfigUpsert'] | undefined,
  token?: string,
) {
  const envelope = await apiFetch<components['schemas']['FeishuDiagnosticApiResponse']>(
    `${getApiBaseUrl()}/api/v1/identity/feishu-config/test`,
    {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : undefined,
      body: JSON.stringify(data || null),
    },
  )
  return unwrapResponse(envelope)
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
