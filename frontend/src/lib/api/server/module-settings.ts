import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { ModuleSetting, ModuleSettingUpdate } from '@/types/module-settings'

// 服务端调用统一走 API_BASE_URL（与其它 lib/api/server/* 模块一致），
// 不依赖 apiFetch 对相对路径的兜底拼接。
const M = (path: string) => `${getApiBaseUrl()}/api/v1/module-settings${path}`

export async function getModuleSettings(
  headers: Record<string, string>,
  module?: string
): Promise<{ data: ModuleSetting[] }> {
  const params = module ? `?module=${module}` : ''
  return apiFetch<{ data: ModuleSetting[] }>(M(params), { headers })
}

export async function getModuleSetting(
  headers: Record<string, string>,
  module: string,
  key: string
): Promise<{ data: ModuleSetting }> {
  return apiFetch<{ data: ModuleSetting }>(M(`/${module}/${key}`), { headers })
}

export async function updateModuleSetting(
  headers: Record<string, string>,
  module: string,
  key: string,
  data: ModuleSettingUpdate
): Promise<{ data: ModuleSetting }> {
  return apiFetch<{ data: ModuleSetting }>(M(`/${module}/${key}`), {
    method: 'PUT',
    headers,
    body: JSON.stringify(data),
  })
}
