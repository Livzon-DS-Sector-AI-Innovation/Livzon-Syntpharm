import { apiFetch } from '@/lib/api/server/base'
import type { ModuleSetting, ModuleSettingUpdate, ModuleSettingCreate } from '@/types/module-settings'

export async function getModuleSettings(
  headers: Record<string, string>,
  module?: string
): Promise<{ data: ModuleSetting[] }> {
  const params = module ? `?module=${module}` : ''
  return apiFetch(`/api/v1/module-settings${params}`, { headers })
}

export async function getModuleSetting(
  headers: Record<string, string>,
  module: string,
  key: string
): Promise<{ data: ModuleSetting }> {
  return apiFetch(`/api/v1/module-settings/${module}/${key}`, { headers })
}

export async function updateModuleSetting(
  headers: Record<string, string>,
  module: string,
  key: string,
  data: ModuleSettingUpdate
): Promise<{ data: ModuleSetting }> {
  return apiFetch(`/api/v1/module-settings/${module}/${key}`, {
    method: 'PUT',
    headers,
    body: JSON.stringify(data),
  })
}

export async function createModuleSetting(
  headers: Record<string, string>,
  data: ModuleSettingCreate
): Promise<{ data: ModuleSetting }> {
  return apiFetch('/api/v1/module-settings', {
    method: 'POST',
    headers,
    body: JSON.stringify(data),
  })
}

export async function deleteModuleSetting(
  headers: Record<string, string>,
  module: string,
  key: string
): Promise<{ message: string }> {
  return apiFetch(`/api/v1/module-settings/${module}/${key}`, {
    method: 'DELETE',
    headers,
  })
}