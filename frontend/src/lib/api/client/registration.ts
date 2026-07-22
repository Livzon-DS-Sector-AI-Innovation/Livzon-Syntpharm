import type { components } from '@/types/generated/schema'
import type {
  Drug,
  DrugNode,
  Holiday,
  ReviewNodeConfig,
  DashboardProjectItem,
  DashboardCertificateItem,
  DashboardSummary,
} from '@/types/registration'

export type DrugCreate = components['schemas']['DrugCreate']
export type DrugUpdate = components['schemas']['DrugUpdate']

export type { Drug, ReviewNodeConfig } from '@/types/registration'

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

export async function fetchModuleInfo(): Promise<{ code: string; name: string; description: string }> {
  return apiFetch(`/api/v1/registration`)
}

// Authorization Letters
// Authorization Letters
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
  const res = await fetch(`/api/v1/registration/authorization-letters${query ? `?${query}` : ''}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json
}

export async function fetchAuthorizationLetterDownloadUrl(id: string): Promise<string> {
  const res = await fetch(`/api/v1/registration/authorization-letters/${id}/download-url`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data.url
}

// Reference Standards
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
  const res = await fetch(`/api/v1/registration/reference-standards${query ? `?${query}` : ''}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json
}

export async function fetchReferenceStandardDownloadUrl(id: string): Promise<string> {
  const res = await fetch(`/api/v1/registration/reference-standards/${id}/download-url`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data.url
}


// Supplementary Replies
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
  const res = await fetch(`/api/v1/registration/supplementary-replies${query ? `?${query}` : ''}`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json
}

export async function fetchSupplementaryReplyDownloadUrl(id: string): Promise<string> {
  const res = await fetch(`/api/v1/registration/supplementary-replies/${id}/download-url`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data.url
}

// ====== 药品 (from registration-client) ======

export async function fetchDrugs(): Promise<Drug[]> {
  const res = await fetch(`/api/v1/registration/drugs/`)
  const json = await res.json()
  return json.data || []
}

export async function fetchDrug(id: string): Promise<Drug> {
  const res = await fetch(`/api/v1/registration/drugs/${id}`)
  const json = await res.json()
  return json.data
}

export async function fetchReviewNodes(): Promise<ReviewNodeConfig[]> {
  const res = await fetch(`/api/v1/registration/drugs/nodes`)
  const json = await res.json()
  return json.data || []
}

export async function fetchHolidays(year?: number): Promise<Holiday[]> {
  const url = year
    ? `/api/v1/registration/holidays/?year=${year}`
    : `/api/v1/registration/holidays/`
  const res = await fetch(url)
  const json = await res.json()
  return json.data || []
}

// Dashboard types and functions (merged from registration-dashboard-client.ts)

export async function fetchDashboardSummary(): Promise<DashboardSummary> {
  const res = await fetch('/api/v1/registration/dashboard/summary')
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data
}
