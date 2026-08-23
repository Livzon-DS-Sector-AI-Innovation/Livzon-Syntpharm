'use server'

import { fetchModuleInfo } from '@/lib/api/server/environment'

export async function fetchModuleInfoAction() {
  return fetchModuleInfo() as any
}