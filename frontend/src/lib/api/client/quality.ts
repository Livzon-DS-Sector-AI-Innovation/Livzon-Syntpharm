import type { ModuleInfo } from '@/types'
import type { components } from '@/types/generated/schema'
import type { DepartmentContactListData, DeviationLedgerDetail } from '@/types/quality'

type CapaResponse = components['schemas']['CapaResponse']
type CapaApiResponse = components['schemas']['CapaApiResponse']

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

export async function fetchDepartmentContacts(keyword?: string): Promise<DepartmentContactListData> {
  const query = keyword ? `?keyword=${encodeURIComponent(keyword)}` : ''
  return apiGet<DepartmentContactListData>(`/api/v1/quality/department-contacts${query}`)
}

// ============ 偏差台账（quality.deviation_ledger） ============

/** 台账只读详情：右侧抽屉按需拉取，只含主表字段 */
export async function fetchDeviationLedgerDetail(id: string): Promise<DeviationLedgerDetail> {
  return apiGet<DeviationLedgerDetail>(`/api/v1/quality/deviation/ledger/${encodeURIComponent(id)}`)
}
