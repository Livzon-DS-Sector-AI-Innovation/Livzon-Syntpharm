import type { components } from '@/types/generated/schema'

export type DrugCreate = components['schemas']['DrugCreate']
export type DrugUpdate = components['schemas']['DrugUpdate']

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

export async function getAuthorizationLetterDownloadUrl(id: string): Promise<string> {
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

export async function getReferenceStandardDownloadUrl(id: string): Promise<string> {
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

export async function getSupplementaryReplyDownloadUrl(id: string): Promise<string> {
  const res = await fetch(`/api/v1/registration/supplementary-replies/${id}/download-url`)
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data.url
}

// ====== 药品 (from registration-client) ======

export interface DrugNode {
  id: string
  drug_id: string
  node_index: number
  actual_date: string | null
  created_at: string
  updated_at: string
}

export interface Drug {
  id: string
  name: string
  type: '仿制药' | '创新药' | '原料药'
  acceptance_date: string
  current_node: number
  created_at: string
  updated_at: string
  nodes: DrugNode[]
}

export interface Holiday {
  id: string
  year: number
  date: string
  type: 'holiday' | 'makeup'
  description: string | null
  created_at: string
  updated_at: string
}

export interface ReviewNodeConfig {
  index: number
  name: string
  days: number
}

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
export interface DashboardProjectItem {
  id: string
  product_name: string
  market: string
  registration_type: string | null
  status: string
  submitted_at: string | null
  accepted_at: string | null
  expected_completion_at: string | null
  owner: string | null
  latest_progress: string | null
}

export interface DashboardCertificateItem {
  id: string
  product_name: string
  certificate_no: string | null
  approved_at: string | null
  valid_until: string | null
  certificate_status: string
  file_path: string | null
}

export interface DashboardSummary {
  approved_product_count: number
  overseas_approval_count: number
  submitted_project_count: number
  active_project_count: number
  recent_projects: DashboardProjectItem[]
  overseas_approvals: DashboardCertificateItem[]
}

export async function getRegistrationDashboardSummary(): Promise<DashboardSummary> {
  const res = await fetch('/api/v1/registration/dashboard/summary')
  if (!res.ok) throw new Error(`请求失败: ${res.status}`)
  const json = await res.json()
  return json.data
}
