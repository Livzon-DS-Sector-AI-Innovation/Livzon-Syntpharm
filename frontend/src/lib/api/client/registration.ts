import type { components } from '@/types/generated/schema'
import type {
  Drug,
  Holiday,
  ReviewNodeConfig,
  DashboardSummary,
} from '@/types/registration'
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

export type DrugCreate = components['schemas']['DrugCreate']
export type DrugUpdate = components['schemas']['DrugUpdate']

export type { Drug, ReviewNodeConfig } from '@/types/registration'

export async function fetchModuleInfo(): Promise<{ code: string; name: string; description: string }> {
  return apiGet(`/api/v1/registration`)
}

export async function fetchAuthorizationLetters(params?: {
  page?: number
  page_size?: number
  product_name?: string
  preparation_unit?: string
}): Promise<{ data: any[]; meta: { total: number } }> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.product_name) searchParams.set('product_name', params.product_name)
  const query = searchParams.toString()
  const result = await apiFetchPaginated<any>(
    `/api/v1/registration/authorization-letters${query ? `?${query}` : ''}`
  )
  return { data: result.items, meta: { total: result.total } }
}

export async function fetchAuthorizationLetterDownloadUrl(id: string): Promise<string> {
  const result = await apiGet<{ url: string }>(
    `/api/v1/registration/authorization-letters/${id}/download-url`
  )
  return result.url
}

export async function fetchReferenceStandards(params?: {
  page?: number
  page_size?: number
  drug_name?: string
}): Promise<{ data: any[]; meta: { total: number } }> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.drug_name) searchParams.set('drug_name', params.drug_name)
  const query = searchParams.toString()
  const result = await apiFetchPaginated<any>(
    `/api/v1/registration/reference-standards${query ? `?${query}` : ''}`
  )
  return { data: result.items, meta: { total: result.total } }
}

export async function fetchReferenceStandardDownloadUrl(id: string): Promise<string> {
  const result = await apiGet<{ url: string }>(
    `/api/v1/registration/reference-standards/${id}/download-url`
  )
  return result.url
}

export async function fetchSupplementaryReplies(params?: {
  page?: number
  page_size?: number
  drug_name?: string
}): Promise<{ data: any[]; meta: { total: number } }> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.drug_name) searchParams.set('drug_name', params.drug_name)
  const query = searchParams.toString()
  const result = await apiFetchPaginated<any>(
    `/api/v1/registration/supplementary-replies${query ? `?${query}` : ''}`
  )
  return { data: result.items, meta: { total: result.total } }
}

export async function fetchSupplementaryReplyDownloadUrl(id: string): Promise<string> {
  const result = await apiGet<{ url: string }>(
    `/api/v1/registration/supplementary-replies/${id}/download-url`
  )
  return result.url
}

export async function fetchDrugs(): Promise<Drug[]> {
  const result = await apiGet<Drug[]>(`/api/v1/registration/drugs/`)
  return result || []
}

export async function fetchDrug(id: string): Promise<Drug> {
  return apiGet<Drug>(`/api/v1/registration/drugs/${id}`)
}

export async function fetchReviewNodes(): Promise<ReviewNodeConfig[]> {
  const result = await apiGet<ReviewNodeConfig[]>(`/api/v1/registration/drugs/nodes`)
  return result || []
}

export async function fetchHolidays(year?: number): Promise<Holiday[]> {
  const url = year
    ? `/api/v1/registration/holidays/?year=${year}`
    : `/api/v1/registration/holidays/`
  const result = await apiGet<Holiday[]>(url)
  return result || []
}

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  return apiGet<DashboardSummary>('/api/v1/registration/dashboard/summary')
}
