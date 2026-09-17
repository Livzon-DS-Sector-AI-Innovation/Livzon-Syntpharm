import type { ModuleInfo } from '@/types'
import type { CapaListResponse, DeviationListResponse, DepartmentContactListResponse } from '@/types/quality'
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiGet(`/api/v1/quality`)
}

export async function fetchCapa(id: string): Promise<any> {
  return apiGet<any>(`/api/v1/quality/capas/${id}`)
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
  return apiFetchPaginated<any>(`/api/v1/quality/capas${query ? `?${query}` : ''}`) as Promise<CapaListResponse>
}

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
  return apiFetchPaginated<any>(`/api/v1/quality/deviations${query ? `?${query}` : ''}`) as Promise<DeviationListResponse>
}

export async function fetchDeviation(id: string): Promise<any> {
  return apiGet<any>(`/api/v1/quality/deviations/${id}`)
}

export async function fetchDepartmentContacts(page: number = 1, page_size: number = 20): Promise<DepartmentContactListResponse> {
  return apiFetchPaginated<any>(`/api/v1/quality/department-contacts?page=${page}&page_size=${page_size}`) as Promise<DepartmentContactListResponse>
}
