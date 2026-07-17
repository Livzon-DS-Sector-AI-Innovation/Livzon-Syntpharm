import type { ModuleInfo } from '@/types'
import type { CapaListResponse, DeviationListResponse, DepartmentContactListResponse } from '@/types/quality'

async function apiFetch<T>(url: string, options?: RequestInit): Promise<T> {
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
  return data.data ?? data
}

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiFetch(`/api/v1/quality`)
}

// CAPA read functions
export async function fetchCapa(id: string): Promise<any> {
  const res = await fetch(`/api/v1/quality/capas/${id}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data || { items: [], total: 0 }
}

export async function fetchCapas(params?: {
  source?: string
  category?: string
  keyword?: string
  page?: number
  page_size?: number
  status?: string
}): Promise<CapaListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.status) searchParams.set('status', params.status)
  const query = searchParams.toString()
  const res = await fetch(`/api/v1/quality/capas${query ? `?${query}` : ''}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data || { items: [], total: 0 }
}

// Deviation read functions
export async function fetchDeviations(params?: {
  level?: string
  department?: string
  keyword?: string
  page?: number
  page_size?: number
  status?: string
}): Promise<DeviationListResponse> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.status) searchParams.set('status', params.status)
  const query = searchParams.toString()
  const res = await fetch(`/api/v1/quality/deviations${query ? `?${query}` : ''}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data || { items: [], total: 0 }
}

export async function fetchDeviation(id: string): Promise<any> {
  const res = await fetch(`/api/v1/quality/deviations/${id}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data || { items: [], total: 0 }
}

// Department Contact read function
export async function fetchDepartmentContacts(page: number = 1, page_size: number = 20): Promise<DepartmentContactListResponse> {
  const res = await fetch(`/api/v1/quality/department-contacts?page=${page}&page_size=${page_size}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data || { items: [], total: 0 }
}
