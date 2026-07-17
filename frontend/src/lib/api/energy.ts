import { apiFetch, API_BASE_URL } from '@/lib/api/server/base'

const API_BASE = API_BASE_URL

export async function fetchWorkshops() {
  return apiFetch(`${API_BASE}/api/v1/energy/workshops`)
}

export async function fetchMonthlyRecords(params: Record<string, unknown> = {}) {
  const qs = new URLSearchParams(params as Record<string, string>).toString()
  return apiFetch(`${API_BASE}/api/v1/energy/monthly${qs ? '?' + qs : ''}`)
}
