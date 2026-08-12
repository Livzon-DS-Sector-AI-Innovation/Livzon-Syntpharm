import {
  ResearchProject,
  ResearchProjectFilters,
  ResearchProjectListResponse,
} from '@/types/research'
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

const API_BASE = '/api/v1'

export async function fetchResearchProjects(
  filters: ResearchProjectFilters = {}
): Promise<ResearchProjectListResponse> {
  const params = new URLSearchParams()
  if (filters.stage) params.set('stage', filters.stage)
  if (filters.status) params.set('status', filters.status)
  if (filters.keyword) params.set('keyword', filters.keyword)
  params.set('project_type', '')
  params.set('page', String(filters.page || 1))
  params.set('page_size', String(filters.page_size || 20))
  return apiFetchPaginated<ResearchProject>(
    `${API_BASE}/research/projects?${params.toString()}`
  )
}

export async function fetchResearchProject(
  projectId: string
): Promise<ResearchProject> {
  return apiGet<ResearchProject>(`${API_BASE}/research/projects/${projectId}`)
}
