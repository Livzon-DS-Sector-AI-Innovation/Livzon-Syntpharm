'use server'

import { fetchModuleInfo as fetchModuleInfoApi } from '@/lib/api/server/purchasing'

export async function fetchModuleInfoAction() {
  return fetchModuleInfoApi()
}