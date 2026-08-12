import type { ModuleInfo } from '@/types/environment'
import { apiGet } from '@/lib/api/client'

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiGet(`/api/v1/environment`)
}
