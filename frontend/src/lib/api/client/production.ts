import type { ModuleInfo } from '@/types'
import { apiGet } from '@/lib/api/client'

export async function fetchModuleInfo(): Promise<ModuleInfo> {
  return apiGet(`/api/v1/production`)
}
