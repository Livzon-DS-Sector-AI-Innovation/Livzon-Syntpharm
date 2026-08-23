import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function fetchRdProjects(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.stage) qs.set('stage', params.stage)
  if (params.status) qs.set('status', params.status)
  if (params.keyword) qs.set('keyword', params.keyword)
  qs.set('page', String(params.page || 1))
  qs.set('page_size', String(params.page_size || 20))
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-projects?${qs}`)
}

export async function fetchRdProject(id: string) {
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/rd-projects/${id}`)
}