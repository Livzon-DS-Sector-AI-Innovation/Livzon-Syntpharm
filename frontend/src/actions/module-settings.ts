'use server'

import { cookies } from 'next/headers'
import {
  getModuleSettings as apiGetModuleSettings,
  getModuleSetting as apiGetModuleSetting,
  updateModuleSetting as apiUpdateModuleSetting,
} from '@/lib/api/server/module-settings'
import type { ModuleSetting, ModuleSettingUpdate } from '@/types/module-settings'

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

export async function getModuleSettings(module?: string): Promise<{ data: ModuleSetting[] }> {
  const headers = await getAuthHeaders()
  return apiGetModuleSettings(headers, module)
}

export async function getModuleSetting(module: string, key: string): Promise<{ data: ModuleSetting }> {
  const headers = await getAuthHeaders()
  return apiGetModuleSetting(headers, module, key)
}

export async function updateModuleSetting(
  module: string,
  key: string,
  data: ModuleSettingUpdate
): Promise<{ data: ModuleSetting }> {
  const headers = await getAuthHeaders()
  return apiUpdateModuleSetting(headers, module, key, data)
}

