import {
  ResearchProject,
  ResearchProjectFilters,
  ResearchProjectListResponse,
} from '@/types/research'
const API_BASE = '/api/v1'

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
  return data.data
}

async function apiFetchPaginated(
  url: string,
  options?: RequestInit
): Promise<ResearchProjectListResponse> {
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
}

export async function fetchResearchProjects(
  filters: ResearchProjectFilters = {}
): Promise<ResearchProjectListResponse> {
  const params = new URLSearchParams()
  if (filters.stage) params.set('stage', filters.stage)
  if (filters.status) params.set('status', filters.status)
  if (filters.keyword) params.set('keyword', filters.keyword)
  params.set('project_type', '')  // Only regular research projects
  params.set('page', String(filters.page || 1))
  params.set('page_size', String(filters.page_size || 20))
  return apiFetchPaginated(
    `${API_BASE}/research/projects?${params.toString()}`
  )
}

export async function fetchResearchProject(
  projectId: string
): Promise<ResearchProject> {
  return apiFetch(`${API_BASE}/research/projects/${projectId}`)
}
