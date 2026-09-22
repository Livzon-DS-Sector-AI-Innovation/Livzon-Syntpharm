import type { ModuleInfo } from '@/types'
import type { components } from '@/types/generated/schema'
import type { DeviationListResponse, DepartmentContactListResponse, DeviationDetail, DepartmentContact, DeviationListItem } from '@/types/quality'

type CapaResponse = components['schemas']['CapaResponse']
type CapaApiResponse = components['schemas']['CapaApiResponse']
type CapaListApiResponse = components['schemas']['CapaListApiResponse']

// Type aliases for backward compatibility
type CapaDetail = CapaResponse
type CapaListItem = CapaResponse
type CapaListResponse = CapaListApiResponse
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiGet(`/api/v1/quality`)
}

export async function fetchCapa(id: string): Promise<CapaApiResponse> {
  return apiGet<CapaApiResponse>(`/api/v1/quality/capas/${id}`)
}

export async function fetchCapas(params?: {
  source?: string
  category?: string
  keyword?: string
  page?: number
  page_size?: number
}): Promise<{ items: CapaResponse[]; total: number; page: number; page_size: number }> {
  const query = params
    ? Object.entries(params)
        .filter(([_, v]) => v !== undefined && v !== null && v !== '')
        .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
        .join('&')
    : ''
  return apiFetchPaginated<CapaResponse>(`/api/v1/quality/capas${query ? `?${query}` : ''}`)
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
  return apiFetchPaginated<DeviationListItem>(`/api/v1/quality/deviations${query ? `?${query}` : ''}`) as Promise<DeviationListResponse>
}

export async function fetchDeviation(id: string): Promise<DeviationDetail> {
  return apiGet<DeviationDetail>(`/api/v1/quality/deviations/${id}`)
}

export async function fetchDepartmentContacts(page: number = 1, page_size: number = 20): Promise<DepartmentContactListResponse> {
  return apiFetchPaginated<DepartmentContact>(`/api/v1/quality/department-contacts?page=${page}&page_size=${page_size}`) as Promise<DepartmentContactListResponse>
}
