import { apiFetch, apiFetchPaginated, getApiBaseUrl, unwrapResponse } from '@/lib/api/server/base'
import type { RdProject } from '@/types/research/rd-project'

export async function fetchRdProjects(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams()
  if (params.stage) qs.set('stage', String(params.stage))
  if (params.status) qs.set('status', String(params.status))
  if (params.keyword) qs.set('keyword', String(params.keyword))
  qs.set('page', String(params.page || 1))
  qs.set('page_size', String(params.page_size || 20))
  return apiFetchPaginated<RdProject>(`${getApiBaseUrl()}/api/v1/research/rd-projects?${qs}`)
}

export async function fetchRdProject(id: string): Promise<RdProject> {
  return unwrapResponse(
    await apiFetch<{ code: number; data: RdProject; message?: string; meta?: unknown }>(
      `${getApiBaseUrl()}/api/v1/research/rd-projects/${id}`,
    ),
  )
}