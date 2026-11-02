import { PermissionDeniedError } from '@/lib/api/errors'

export function getApiBaseUrl(): string {
  if (process.env.API_BASE_URL) {
    return process.env.API_BASE_URL
  }
  
  throw new Error(
    'API_BASE_URL environment variable is not set. ' +
    'Please set it to the backend API base URL (e.g., http://localhost:8000 for development).'
  )
}

async function getAuthHeaders(): Promise<Record<string, string>> {
  try {
    const { cookies } = await import('next/headers')
    const cookieStore = await cookies()
    const authCookie = cookieStore.get('auth_token')
    if (authCookie?.value) {
      return { Authorization: `Bearer ${authCookie.value}` }
    }
  } catch {
    // Not in a request context
  }
  return {}
}

async function fetchWithRetry(url: string, options: RequestInit, maxRetries = 2): Promise<Response> {
  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fetch(url, options)
    } catch (error) {
      if (attempt === maxRetries) throw error
      await new Promise(resolve => setTimeout(resolve, 500 * (attempt + 1)))
    }
  }
  throw new Error('unreachable')
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- apiFetch is used by 755+ call sites; changing default from any to unknown would require updating all call sites with explicit type parameters or assertions
export async function apiFetch<T = any>(url: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders()

  // 当 body 是 FormData 时，不设置 Content-Type，让浏览器自动设置 multipart/form-data
  const isFormData = options?.body instanceof FormData || 
    (options?.body && typeof FormData !== 'undefined' && options?.body.constructor?.name === 'FormData')
  const response = await fetchWithRetry(url.startsWith('http') ? url : `${getApiBaseUrl()}${url}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...authHeaders,
      ...options?.headers,
    },
    cache: options?.cache ?? 'no-store',
  })
  if (!response.ok) {
    let errorMessage = `请求失败: ${response.status} ${response.statusText}`
    try {
      const errorJson = await response.json()
      if (errorJson.message) errorMessage = errorJson.message
      else if (errorJson.detail) errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail)
    } catch {
      // 非 JSON 响应，保留默认文案
    }
    // 403 单独语义化：由调用方统一提示「当前用户权限不足」，不把技术状态码抛给用户
    if (response.status === 403) {
      throw new PermissionDeniedError(errorMessage)
    }
    throw new Error(errorMessage)
  }
  // 204 No Content（如软删除接口）或空响应体：没有 JSON 可解析，直接返回 null。
  // 否则 response.json() 会抛 "Unexpected end of JSON input"，调用方误报「操作失败」，
  // 而数据其实已经删除成功。
  if (response.status === 204) return null as T
  const text = await response.text()
  if (!text) return null as T
  return JSON.parse(text) as T
}

/**
 * 在 `apiFetch` 基础上直接返回信封里的 `data`。
 * 需要响应的业务数据、又不想在每个调用点重复 `.data` 解包时使用。
 */
export async function apiFetchData<T>(url: string, options?: RequestInit): Promise<T> {
  const result = await apiFetch<T>(url, options)
  if (result && typeof result === 'object' && 'data' in (result as Record<string, unknown>)) {
    return (result as unknown as { data: T }).data
  }
  return result
}

export async function apiFetchRaw(url: string, options?: RequestInit): Promise<Response> {
  const authHeaders = await getAuthHeaders()

  // 当 body 是 FormData 时，不设置 Content-Type，让浏览器自动设置 multipart/form-data
  const isFormData = options?.body instanceof FormData || 
    (options?.body && typeof FormData !== 'undefined' && options?.body.constructor?.name === 'FormData')
  const response = await fetch(url.startsWith('http') ? url : `${getApiBaseUrl()}${url}`, {
    ...options,
    headers: {
      ...(isFormData ? {} : { 'Content-Type': 'application/json' }),
      ...authHeaders,
      ...options?.headers,
    },
    cache: options?.cache ?? 'no-store',
  })
  if (!response.ok) {
    const errorBody = await response.text().catch(() => '')
    throw new Error(`请求失败: ${response.status} - ${errorBody}`)
  }
  return response
}

export async function safeApiFetch<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<{ code: number; message: string; data: T; meta?: { page?: number; page_size?: number; total?: number } }> {
  const authHeaders = await getAuthHeaders()

  let response: Response
  try {
    response = await fetchWithRetry(`${getApiBaseUrl()}${endpoint}`, {
      ...options,
      headers: {
        ...authHeaders,
        ...options?.headers,
      },
    })
  } catch {
    return {
      code: -1,
      message: '网络请求失败，无法连接到后端服务',
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
    } catch {}
    return { code: response.status, message: errorMessage, data: null as unknown as T }
  }

  try {
    return await response.json()
  } catch {
    const text = await response.text().catch(() => '无法读取响应')
    return { code: -1, message: `响应解析失败: ${text.substring(0, 200)}`, data: null as unknown as T }
  }
}

export async function apiFetchPaginated<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<{ items: T[]; total: number; page: number; page_size: number }> {
  const result = await apiFetch<{ code: number; data: T[]; message?: string; meta?: { page?: number; page_size?: number; total?: number } }>(endpoint, options)
  return {
    items: unwrapResponse(result),
    total: result.meta?.total || 0,
    page: result.meta?.page || 1,
    page_size: result.meta?.page_size || 20,
  }
}

/**
 * Extract the `data` payload from a wrapped API response envelope.
 * All server-side API responses follow the shape `{code, data, message, meta}`.
 * Use this helper instead of ad-hoc `.data` access at call sites.
 */
export function unwrapResponse<T>(raw: { code: number; data: T; message?: string; meta?: unknown }): T {
  return raw.data
}

export function buildQueryString(params: Record<string, unknown>): string {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  const qs = searchParams.toString()
  return qs ? `?${qs}` : ''
}
