'use server'

import { cookies } from 'next/headers'
import {
  getModuleSettings as apiGetModuleSettings,
  getModuleSetting as apiGetModuleSetting,
  updateModuleSetting as apiUpdateModuleSetting,
  createModuleSetting as apiCreateModuleSetting,
  deleteModuleSetting as apiDeleteModuleSetting,
} from '@/lib/api/server/module-settings'

export type {
  ModuleSetting,
  ModuleSettingUpdate,
  ModuleSettingCreate,
} from '@/lib/api/server/module-settings'

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

export async function getModuleSettings(module?: string): Promise<{ data: import('@/lib/api/server/module-settings').ModuleSetting[] }> {
  const headers = await getAuthHeaders()
  return apiGetModuleSettings(headers, module)
}

export async function getModuleSetting(module: string, key: string): Promise<{ data: import('@/lib/api/server/module-settings').ModuleSetting }> {
  const headers = await getAuthHeaders()
  return apiGetModuleSetting(headers, module, key)
}

export async function updateModuleSetting(
  module: string,
  key: string,
  data: import('@/lib/api/server/module-settings').ModuleSettingUpdate
): Promise<{ data: import('@/lib/api/server/module-settings').ModuleSetting }> {
  const headers = await getAuthHeaders()
  return apiUpdateModuleSetting(headers, module, key, data)
}

export async function createModuleSetting(
  data: import('@/lib/api/server/module-settings').ModuleSettingCreate
): Promise<{ data: import('@/lib/api/server/module-settings').ModuleSetting }> {
  const headers = await getAuthHeaders()
  return apiCreateModuleSetting(headers, data)
}

export async function deleteModuleSetting(
  module: string,
  key: string
): Promise<{ message: string }> {
  const headers = await getAuthHeaders()
  return apiDeleteModuleSetting(headers, module, key)
}