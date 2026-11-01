import type { ModuleInfo } from '@/types'
import type { components } from '@/types/generated/schema'
import type { DepartmentContactListResponse, DeviationDetail, DepartmentContact } from '@/types/quality'

type CapaResponse = components['schemas']['CapaResponse']
type CapaApiResponse = components['schemas']['CapaApiResponse']
type DeviationResponse = components['schemas']['DeviationResponse']

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
}): Promise<{ items: DeviationResponse[]; total: number; page: number; page_size: number }> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.status) searchParams.set('status', params.status)
  const query = searchParams.toString()
  return apiFetchPaginated<DeviationResponse>(`/api/v1/quality/deviations${query ? `?${query}` : ''}`)
}

export async function fetchDeviation(id: string): Promise<DeviationDetail> {
  return apiGet<DeviationDetail>(`/api/v1/quality/deviations/${id}`)
}

export async function fetchDepartmentContacts(page: number = 1, page_size: number = 20): Promise<DepartmentContactListResponse> {
  return apiFetchPaginated<DepartmentContact>(`/api/v1/quality/department-contacts?page=${page}&page_size=${page_size}`) as Promise<DepartmentContactListResponse>
}

// ============ 偏差流程（deviation-flow） ============

export interface DeviationFlowListItem {
  id: string
  deviation_no: string
  theme?: string | null
  status: string
  status_label?: string | null
  deviation_type?: string | null
  deviation_type_label?: string | null
  urgency_level?: string | null
  urgency_level_label?: string | null
  responsible_department?: string | null
  occurred_date?: string | null
  reporter?: string | null
  remaining_days?: number | null
  completed_days?: number | null
}

export interface DeviationFlowListData<T = DeviationFlowListItem> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface DeviationFlowQuery {
  page?: number
  page_size?: number
  keyword?: string
  status?: string
  deviation_type?: string
  urgency_level?: string
  start_date?: string
  end_date?: string
}

export async function fetchDeviationFlowList<T = DeviationFlowListItem>(
  params: DeviationFlowQuery = {},
): Promise<DeviationFlowListData<T>> {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      searchParams.set(key, String(value))
    }
  })
  const query = searchParams.toString()
  return apiGet<DeviationFlowListData<T>>(`/api/v1/quality/deviation-flow${query ? `?${query}` : ''}`)
}

export interface DeviationFlowDetail {
  id: string
  deviation_no: string
  theme?: string | null
  status: string
  status_label?: string | null
  deviation_type?: string | null
  deviation_type_label?: string | null
  urgency_level?: string | null
  urgency_level_label?: string | null
  responsible_department?: string | null
  occurred_area?: string | null
  occurred_date?: string | null
  discovered_date?: string | null
  product_name?: string | null
  batch_no?: string | null
  equipment?: string | null
  standard_based_on?: string | null
  deviation_description?: string | null
  risk_assessment?: string | null
  temp_measures?: string | null
  related_deviation_no?: string | null
  related_capa?: string | null
  remarks?: string | null
  reporter?: string | null
  reporter_department?: string | null
  report_time?: string | null
  created_at?: string | null
  updated_at?: string | null
  qa_feishu_name?: string | null
  dept_leader_feishu_name?: string | null
}

export async function fetchDeviationFlowDetail<T = DeviationFlowDetail>(id: string): Promise<T> {
  return apiGet<T>(`/api/v1/quality/deviation-flow/${encodeURIComponent(id)}`)
}
