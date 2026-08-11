import type { ModuleInfo } from '@/types/safety'
import { apiGet } from '@/lib/api/client'

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiGet(`/api/v1/safety`)
}
