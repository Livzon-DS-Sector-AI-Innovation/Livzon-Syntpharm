import type { components } from '@/types/generated/schema'
import type {
  Drug,
  DrugPrediction,
  Holiday,
  ReviewNodeConfig,
  DashboardSummary,
  AuthorizationLetterListItem,
  AuthorizationLetterTrail,
  AuthorizationLetterFilterOptions,
  ReferenceStandardListItem,
  SupplementaryReplyListItem,
  RegistrationProject,
} from '@/types/registration'
import { apiGet, apiFetchPaginated } from '@/lib/api/client'
import type { PageResult } from '@/lib/api/page'

export type DrugCreate = components['schemas']['DrugCreate']
export type DrugUpdate = components['schemas']['DrugUpdate']

export type { Drug, ReviewNodeConfig } from '@/types/registration'

export async function fetchModuleInfo(): Promise<{ code: string; name: string; description: string }> {
  return apiGet(`/api/v1/registration/`)
}

export async function fetchAuthorizationLetters(params?: {
  page?: number
  page_size?: number
  keyword?: string
  product_name?: string
  year?: number
}): Promise<PageResult<AuthorizationLetterListItem>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.keyword) searchParams.set('keyword', params.keyword)
  if (params?.product_name) searchParams.set('product_name', params.product_name)
  if (params?.year) searchParams.set('year', String(params.year))
  const query = searchParams.toString()
  return apiFetchPaginated<AuthorizationLetterListItem>(
    `/api/v1/registration/authorization-letters${query ? `?${query}` : ''}`
  )
}

export async function fetchAuthorizationLetterDownloadUrl(id: string): Promise<string> {
  const result = await apiGet<{ url: string }>(
    `/api/v1/registration/authorization-letters/${id}/download-url`
  )
  return result.url
}

/** 筛选下拉选项：品种（主数据 ∪ 已有记录）+ 年份（降序） */
export async function fetchAuthorizationLetterFilterOptions(): Promise<AuthorizationLetterFilterOptions> {
  return apiGet<AuthorizationLetterFilterOptions>(
    '/api/v1/registration/authorization-letters/filter-options'
  )
}

/** 授权书留痕时间线（生成/下载，新→旧倒序） */
export async function fetchAuthorizationLetterTrails(letterId: string): Promise<AuthorizationLetterTrail[]> {
  const result = await apiGet<AuthorizationLetterTrail[]>(
    `/api/v1/registration/authorization-letters/${letterId}/trails`
  )
  return result || []
}

export async function fetchReferenceStandards(params?: {
  page?: number
  page_size?: number
  drug_name?: string
}): Promise<PageResult<ReferenceStandardListItem>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.drug_name) searchParams.set('drug_name', params.drug_name)
  const query = searchParams.toString()
  return apiFetchPaginated<ReferenceStandardListItem>(
    `/api/v1/registration/reference-standards${query ? `?${query}` : ''}`
  )
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
}): Promise<PageResult<SupplementaryReplyListItem>> {
  const searchParams = new URLSearchParams()
  if (params?.page) searchParams.set('page', String(params.page))
  if (params?.page_size) searchParams.set('page_size', String(params.page_size))
  if (params?.drug_name) searchParams.set('drug_name', params.drug_name)
  const query = searchParams.toString()
  return apiFetchPaginated<SupplementaryReplyListItem>(
    `/api/v1/registration/supplementary-replies${query ? `?${query}` : ''}`
  )
}

export async function fetchSupplementaryReplyDownloadUrl(id: string): Promise<string> {
  const result = await apiGet<{ url: string }>(
    `/api/v1/registration/supplementary-replies/${id}/download-url`
  )
  return result.url
}

export async function fetchDrugs(): Promise<Drug[]> {
  const result = await apiGet<Drug[]>(`/api/v1/registration/drugs`)
  return result || []
}

export async function fetchDrug(id: string): Promise<Drug> {
  return apiGet<Drug>(`/api/v1/registration/drugs/${id}`)
}

export async function fetchDrugPrediction(id: string): Promise<DrugPrediction> {
  return apiGet<DrugPrediction>(`/api/v1/registration/drugs/${id}/prediction`)
}

export async function fetchReviewNodes(): Promise<ReviewNodeConfig[]> {
  const result = await apiGet<ReviewNodeConfig[]>(`/api/v1/registration/drugs/nodes`)
  return result || []
}

/** 按审评品种反查关联的注册项目（抽屉里展示用） */
export async function fetchProjectsByDrug(drugId: string): Promise<RegistrationProject[]> {
  const result = await apiGet<RegistrationProject[]>(
    `/api/v1/registration/projects/?drug_id=${drugId}`,
  )
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
