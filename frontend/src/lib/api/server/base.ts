const API_BASE_URL = process.env.API_BASE_URL || 'http://dazah-backend-app-1:8000'

async function getAuthHeaders(): Promise<Record<string, string>> {
  try {
    const { cookies } = await import('next/headers')
    const cookieStore = await cookies()
    const authCookie = cookieStore.get('auth_token')
    if (authCookie?.value) {
      return { Authorization: `Bearer ${authCookie.value}` }
    }
  } catch {
    // Not in a request context (e.g. build time or client component)
  }
  return {}
}

export async function apiFetch<T = any>(url: string, options?: RequestInit): Promise<T> {
  const authHeaders = await getAuthHeaders()

  const response = await fetch(url.startsWith('http') ? url : `${API_BASE_URL}${url}`, {
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

  const response = await fetch(url.startsWith('http') ? url : `${API_BASE_URL}${url}`, {
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

export { API_BASE_URL }