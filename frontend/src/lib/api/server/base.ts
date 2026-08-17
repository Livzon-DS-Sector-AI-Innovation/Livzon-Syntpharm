export function getApiBaseUrl(): string {
  return process.env.API_BASE_URL || 'http://backend:8000'
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
    const _errorBody = await response.text().catch(() => '')
    let errorMessage = `请求失败: ${response.status} ${response.statusText}`
    try {
      const errorJson = await response.json()
      if (errorJson.message) errorMessage = errorJson.message
      else if (errorJson.detail) errorMessage = typeof errorJson.detail === 'string' ? errorJson.detail : JSON.stringify(errorJson.detail)
    } catch {}
    throw new Error(errorMessage)
  }
  const result = await response.json()
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
      message: `网络请求失败，无法连接到后端服务 (${getApiBaseUrl()}${endpoint})`,
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
