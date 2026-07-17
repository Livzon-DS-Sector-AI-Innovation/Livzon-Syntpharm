import { apiFetch, API_BASE_URL } from '@/lib/api/server/base'

export async function fetchModuleInfo() {
  return apiFetch(`${API_BASE_URL}/api/v1/environment`)
}