import { apiFetch, API_BASE_URL } from '@/lib/api/server/base'

export async function fetchRdProjects(params: any = {}) {
  const qs = new URLSearchParams()
  if (params.stage) qs.set('stage', params.stage)
  if (params.status) qs.set('status', params.status)
  if (params.keyword) qs.set('keyword', params.keyword)
  qs.set('page', String(params.page || 1))
  qs.set('page_size', String(params.page_size || 20))
  return apiFetch(`${API_BASE_URL}/api/v1/research/rd-projects?${qs}`)
}

export async function fetchRdProject(id: string) {
  return apiFetch(`${API_BASE_URL}/api/v1/research/rd-projects/${id}`)
}