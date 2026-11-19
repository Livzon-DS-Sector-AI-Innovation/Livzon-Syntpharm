import { apiFetchData, getApiBaseUrl } from '@/lib/api/server/base'
import type {
  ModuleSetting,
  ModuleSettingBatchResult,
  ModuleSettingBatchUpdate,
  ModuleSettingUpdate,
} from '@/types/module-settings'

// 服务端调用统一走 API_BASE_URL（与其它 lib/api/server/* 模块一致），
// 不依赖 apiFetch 对相对路径的兜底拼接。
const M = (path: string) => `${getApiBaseUrl()}/api/v1/module-settings${path}`

export async function getModuleSettings(
  headers: Record<string, string>,
  module?: string
): Promise<ModuleSetting[]> {
  const params = module ? `?module=${module}` : ''
  return apiFetchData<ModuleSetting[]>(M(params), { headers })
}

export async function getModuleSetting(
  headers: Record<string, string>,
  module: string,
  key: string
): Promise<ModuleSetting> {
  return apiFetchData<ModuleSetting>(M(`/${module}/${key}`), { headers })
}

export async function updateModuleSetting(
  headers: Record<string, string>,
  module: string,
  key: string,
  data: ModuleSettingUpdate
): Promise<ModuleSetting> {
  return apiFetchData<ModuleSetting>(M(`/${module}/${key}`), {
    method: 'PUT',
    headers,
    body: JSON.stringify(data),
  })
}

/** 批量更新（布尔项批量启停等），失败项逐条返回原因。 */
export async function batchUpdateModuleSettings(
  headers: Record<string, string>,
  data: ModuleSettingBatchUpdate
): Promise<ModuleSettingBatchResult> {
  return apiFetchData<ModuleSettingBatchResult>(M('/batch'), {
    method: 'PUT',
    headers,
    body: JSON.stringify(data),
  })
}