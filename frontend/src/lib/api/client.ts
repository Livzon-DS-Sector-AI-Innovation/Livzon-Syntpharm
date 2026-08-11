/**
 * 统一的 API 客户端工具
 * 提供增强的错误处理，避免 JSON 解析错误导致页面崩溃
 */

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public message: string,
    public data?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

/**
 * 增强的 fetch 函数
 * - 检查 HTTP 状态码
 * - 检查 Content-Type
 * - 统一错误格式
 * - 避免 JSON 解析错误
 */
export async function fetchApi<T>(
  url: string,
  options?: RequestInit
): Promise<T> {
  let response: Response

  try {
    response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })
  } catch (error) {
    // 网络错误
    console.error('[API] Network error:', url, error)
    throw new ApiError(0, 'Network Error', '网络连接失败，请检查网络')
  }

  // 检查 HTTP 状态码
  if (!response.ok) {
    const errorMessages: Record<number, string> = {
      400: '请求参数错误',
      401: '未授权，请重新登录',
      403: '拒绝访问',
      404: '请求的资源不存在',
      408: '请求超时',
      500: '服务器内部错误',
      502: '网关错误',
      503: '服务不可用',
      504: '网关超时',
    }

    const message = errorMessages[response.status] || `请求失败: ${response.status}`
    
    // 尝试解析错误响应（可能是 JSON 格式的错误信息）
    let errorData: any = null
    const contentType = response.headers.get('content-type')
    
    if (contentType?.includes('application/json')) {
      try {
        errorData = await response.json()
      } catch {
        // 忽略 JSON 解析错误
      }
    }

    console.error('[API] HTTP error:', url, response.status, errorData)
    throw new ApiError(response.status, response.statusText, message, errorData)
  }

  // 检查 Content-Type
  const contentType = response.headers.get('content-type')
  
  // 如果是 JSON 响应，解析并返回
  if (contentType?.includes('application/json')) {
    try {
      return await response.json()
    } catch (error) {
      console.error('[API] JSON parse error:', url, error)
      throw new ApiError(
        response.status,
        response.statusText,
        '响应格式错误：无法解析 JSON'
      )
    }
  }

  // 如果是空响应（204 No Content）
  if (response.status === 204 || !contentType) {
    return {} as T
  }

  // 其他类型的响应（text/html 等）
  console.warn('[API] Unexpected content type:', contentType, url)
  throw new ApiError(
    response.status,
    response.statusText,
    `响应格式错误：期望 JSON，实际为 ${contentType}`
  )
}

/**
 * 安全的 JSON 解析
 * 避免 JSON.parse 抛出 SyntaxError
 */
export function safeJsonParse<T>(text: string, fallback: T): T {
  try {
    return JSON.parse(text)
  } catch {
    return fallback
  }
}

export async function apiGet<T>(url: string, options?: RequestInit): Promise<T> {
  const json = await fetchApi<{ code: number; data: T; message?: string; meta?: unknown }>(url, { ...options, method: 'GET' })
  return json.data
}

export async function apiPost<T>(url: string, body?: unknown, options?: RequestInit): Promise<T> {
  const json = await fetchApi<{ code: number; data: T; message?: string; meta?: unknown }>(url, {
    ...options,
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  })
  return json.data
}

export async function apiFetchPaginated<T>(
  url: string,
  options?: RequestInit,
): Promise<{ items: T[]; total: number; page: number; page_size: number }> {
  const result = await fetchApi<{ code: number; data: T[]; message?: string; meta?: { page?: number; page_size?: number; total?: number } }>(url, options)
  return {
    items: result.data || [],
    total: result.meta?.total || 0,
    page: result.meta?.page || 1,
    page_size: result.meta?.page_size || 20,
  }
}
