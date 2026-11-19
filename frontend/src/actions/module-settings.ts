'use server'

import { cookies } from 'next/headers'
import {
  batchUpdateModuleSettings as apiBatchUpdateModuleSettings,
  getModuleSettings as apiGetModuleSettings,
  getModuleSetting as apiGetModuleSetting,
  updateModuleSetting as apiUpdateModuleSetting,
} from '@/lib/api/server/module-settings'
import type {
  ModuleSetting,
  ModuleSettingBatchResult,
  ModuleSettingBatchUpdate,
  ModuleSettingUpdate,
} from '@/types/module-settings'

async function getAuthHeaders(): Promise<Record<string, string>> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
  }
  if (token?.value) {
    headers['Authorization'] = `Bearer ${token.value}`
  }
  return headers
}

export async function getModuleSettings(module?: string): Promise<ModuleSetting[]> {
  const headers = await getAuthHeaders()
  return apiGetModuleSettings(headers, module)
}

export async function getModuleSetting(module: string, key: string): Promise<ModuleSetting> {
  const headers = await getAuthHeaders()
  return apiGetModuleSetting(headers, module, key)
}

export async function updateModuleSetting(
  module: string,
  key: string,
  data: ModuleSettingUpdate
): Promise<ModuleSetting> {
  const headers = await getAuthHeaders()
  return apiUpdateModuleSetting(headers, module, key, data)
}

export async function batchUpdateModuleSettings(
  data: ModuleSettingBatchUpdate
): Promise<ModuleSettingBatchResult> {
  const headers = await getAuthHeaders()
  return apiBatchUpdateModuleSettings(headers, data)
}

