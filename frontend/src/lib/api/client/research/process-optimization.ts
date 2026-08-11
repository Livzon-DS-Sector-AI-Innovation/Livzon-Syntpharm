import {
  ProcessOptimization,
  OptimizationFilters,
  OptimizationListResponse,
  OptimizationCreate,
  OptimizationUpdate,
} from '@/types/research'
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

const API_BASE = '/api/v1'

export async function fetchOptimizations(
  filters: OptimizationFilters = {}
): Promise<OptimizationListResponse> {
  const params = new URLSearchParams()
  if (filters.project_id) params.set('project_id', filters.project_id)
  if (filters.status) params.set('status', filters.status)
  if (filters.keyword) params.set('keyword', filters.keyword)
  params.set('page', String(filters.page || 1))
  params.set('page_size', String(filters.page_size || 20))
  return apiFetchPaginated<ProcessOptimization>(
    `${API_BASE}/research/optimizations?${params.toString()}`
  )
}

export async function fetchOptimizationById(id: string): Promise<ProcessOptimization> {
  return apiGet<ProcessOptimization>(`${API_BASE}/research/optimizations/${id}`)
}
