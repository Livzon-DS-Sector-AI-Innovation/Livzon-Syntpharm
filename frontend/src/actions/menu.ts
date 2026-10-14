'use server'

import { cookies } from 'next/headers'
import { getMenuConfigApi, saveMenuConfigApi } from '@/lib/api/server/menu'
import { EMPTY_MENU_CONFIG, type MenuConfigData } from '@/types/menu-admin'

export interface MenuActionState {
  ok: boolean
  message: string
}

/**
 * 读取菜单栏配置。
 *
 * 失败时返回空配置（前端按代码默认渲染）—— 菜单是导航基础设施，
 * 配置读不到不能让整个导航消失。
 */
export async function getMenuConfig(): Promise<MenuConfigData> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')?.value
  if (!token) return EMPTY_MENU_CONFIG

  try {
    // apiFetch 返回完整信封 { code, data, message }，必须解包 data
    const res = (await getMenuConfigApi(token)) as { data?: MenuConfigData }
    const data = res?.data
    if (!data) return EMPTY_MENU_CONFIG
    return { items: data.items ?? {}, custom: data.custom ?? [] }
  } catch {
    return EMPTY_MENU_CONFIG
  }
}

/** 保存菜单栏配置（业务错误不抛异常，返回 {ok,message}）。 */
export async function saveMenuConfig(data: MenuConfigData): Promise<MenuActionState> {
  const cookieStore = await cookies()
  const token = cookieStore.get('auth_token')?.value
  if (!token) return { ok: false, message: '未登录' }

  try {
    await saveMenuConfigApi(data, token)
    return { ok: true, message: '菜单配置已保存' }
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? (error.message || '保存失败') : '保存失败',
    }
  }
}
