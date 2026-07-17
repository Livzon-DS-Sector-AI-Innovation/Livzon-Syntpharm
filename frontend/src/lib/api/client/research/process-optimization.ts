import {
  ProcessOptimization,
  OptimizationFilters,
  OptimizationListResponse,
  OptimizationCreate,
  OptimizationUpdate,
} from '@/types/research'
const API_BASE = '/api/v1'

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })
    if (!response.ok) {
      throw new Error(`请求失败: ${response.status} ${response.statusText}`)
    }
    const data = await response.json()
    return data.data
  } catch (error) {
    if (error instanceof Error && (
      error.message.includes('Failed to fetch') ||
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('fetch failed')
    )) {
      throw new Error('后端服务不可用，请检查 API 服务器是否启动')
    }
    throw error
  }
}

async function apiFetchPaginated(
  url: string,
  options?: RequestInit
): Promise<OptimizationListResponse> {
  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
    })
    if (!response.ok) {
      throw new Error(`请求失败: ${response.status} ${response.statusText}`)
    }
    const result = await response.json()
    return {
      items: result.data || [],
      total: result.meta?.total || 0,
      page: result.meta?.page || 1,
      page_size: result.meta?.page_size || 20,
    }
  } catch (error) {
    if (error instanceof Error && (
      error.message.includes('Failed to fetch') ||
      error.message.includes('ECONNREFUSED') ||
      error.message.includes('fetch failed')
    )) {
      return {
        items: [],
        total: 0,
        page: 1,
        page_size: 20,
      }
    }
    throw error
  }
}

export async function fetchOptimizations(
  filters: OptimizationFilters = {}
): Promise<OptimizationListResponse> {
  const params = new URLSearchParams()
  if (filters.project_id) params.set('project_id', filters.project_id)
  if (filters.status) params.set('status', filters.status)
  if (filters.keyword) params.set('keyword', filters.keyword)
  params.set('page', String(filters.page || 1))
  params.set('page_size', String(filters.page_size || 20))
  return apiFetchPaginated(
    `${API_BASE}/research/optimizations?${params.toString()}`
  )
}

export async function fetchOptimizationById(id: string): Promise<ProcessOptimization> {
  return apiFetch(`${API_BASE}/research/optimizations/${id}`)
}

