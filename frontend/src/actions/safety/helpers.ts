'use server'

import { revalidatePath } from 'next/cache'
import { getAuthHeaders } from '@/lib/auth'
import { getApiBaseUrl } from '@/lib/api/server/base'

function getApiV1Url(): string {
  return `${getApiBaseUrl()}/api/v1`
}

export async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit
): Promise<{ code: number; message: string; data: T; meta?: { page?: number; page_size?: number; total?: number } }> {
  let response: Response
  try {
    const authHeaders = await getAuthHeaders()
    const { headers: optHeaders, ...restOptions } = options || {}
    response = await fetch(`${getApiV1Url()}${endpoint}`, {
      headers: { ...authHeaders, ...optHeaders },
      ...restOptions,
    })
  } catch {
    return {
      code: -1,
      message: `网络请求失败，无法连接到后端服务 (${getApiV1Url()}${endpoint})`,
      data: null as unknown as T,
    }
  }

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`
    try {
      const errorBody = await response.text()
      try {
        const errorJson = JSON.parse(errorBody)
        if (errorJson.message) errorMessage = errorJson.message
        else if (errorJson.detail) errorMessage = errorJson.detail
      } catch {
        errorMessage = errorBody.substring(0, 200)
      }
    } catch { /* 无法读取响应体 */ }
    return { code: response.status, message: errorMessage, data: null as unknown as T }
  }

  try {
    return await response.json()
  } catch {
    const text = await response.text().catch(() => '无法读取响应')
    return { code: -1, message: `响应解析失败: ${text.substring(0, 200)}`, data: null as unknown as T }
  }
}

export async function uploadPhoto(endpoint: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  const authHeaders = await getAuthHeaders()
  const { 'Content-Type': _, ...uploadHeaders } = authHeaders
  const response = await fetch(`${getApiV1Url()}${endpoint}`, {
    method: 'POST',
    headers: uploadHeaders,
    body: formData,
  })
  if (!response.ok) {
    let detail = ''
    try {
      const err = await response.json()
      detail = err.detail || err.message || ''
    } catch { /* ignore */ }
    throw new Error(`HTTP ${response.status}${detail ? ': ' + detail : ''}`)
  }
  revalidatePath('/safety/hazard')
  return response.json()
}
