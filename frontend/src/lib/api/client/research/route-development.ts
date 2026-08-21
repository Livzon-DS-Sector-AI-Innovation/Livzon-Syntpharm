import {
  RouteDevelopment,
  RouteFilters,
  RouteListResponse,
} from '@/types/research'
import { apiGet, apiFetchPaginated } from '@/lib/api/client'

const API_BASE = '/api/v1'

export async function fetchRoutes(
  filters: RouteFilters = {}
): Promise<RouteListResponse> {
  const params = new URLSearchParams()
  if (filters.project_id) params.set('project_id', filters.project_id)
  if (filters.status) params.set('status', filters.status)
  if (filters.keyword) params.set('keyword', filters.keyword)
  params.set('page', String(filters.page || 1))
  params.set('page_size', String(filters.page_size || 20))
  return apiFetchPaginated<RouteDevelopment>(
    `${API_BASE}/research/routes?${params.toString()}`
  )
}

export async function fetchRouteById(routeId: string): Promise<RouteDevelopment> {
  return apiGet<RouteDevelopment>(`${API_BASE}/research/routes/${routeId}`)
}
