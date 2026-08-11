export function getApiBaseUrl(): string {
  return process.env.API_BASE_URL || 'http://localhost:8000'
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

export async function apiFetch<T = any>(url: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders()

  const response = await fetch(url.startsWith('http') ? url : `${getApiBaseUrl()}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders,
      ...options?.headers,
    },
    cache: options?.cache ?? 'no-store',
  })
  if (!response.ok) {
    const errorBody = await response.text().catch(() => '')
    let errorMessage = `请求失败: ${response.status} ${response.statusText}`
    try {
      const errorJson = JSON.parse(errorBody)
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

  const response = await fetch(url.startsWith('http') ? url : `${getApiBaseUrl()}${url}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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