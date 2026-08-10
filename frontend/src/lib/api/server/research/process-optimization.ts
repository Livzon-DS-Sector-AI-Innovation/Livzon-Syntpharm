import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function fetchOptimizations(filters: any = {}) {
  const params = new URLSearchParams()
  if (filters.project_id) params.set('project_id', filters.project_id)
  if (filters.status) params.set('status', filters.status)
  if (filters.page) params.set('page', String(filters.page))
  if (filters.page_size) params.set('page_size', String(filters.page_size))
  const qs = params.toString()
  return apiFetch(`${getApiBaseUrl()}/api/v1/research/optimizations${qs ? `?${qs}` : ''}`)
}