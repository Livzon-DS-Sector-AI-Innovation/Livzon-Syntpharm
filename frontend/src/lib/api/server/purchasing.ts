import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'

export async function fetchModuleInfo() {
  return apiFetch(`${getApiBaseUrl()}/api/v1/procurement`, { cache: 'no-store' })
}