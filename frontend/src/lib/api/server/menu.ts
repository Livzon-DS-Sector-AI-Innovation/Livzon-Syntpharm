import { apiFetch, getApiBaseUrl } from '@/lib/api/server/base'
import type { MenuConfigData } from '@/types/menu-admin'

const S = (path: string) => `${getApiBaseUrl()}/api/v1/system/menus${path}`

function auth(token?: string): Record<string, string> | undefined {
  return token ? { Authorization: `Bearer ${token}` } : undefined
}

/** 读取菜单栏配置（返回完整信封，调用方需解包 data）。 */
export function getMenuConfigApi(token?: string) {
  return apiFetch(S('/config'), { headers: auth(token) })
}

/** 保存菜单栏配置（返回完整信封）。 */
export function saveMenuConfigApi(data: MenuConfigData, token?: string) {
  return apiFetch(S('/config'), {
    method: 'PUT',
    headers: auth(token),
    body: JSON.stringify({ items: data.items, custom: data.custom }),
  })
}
