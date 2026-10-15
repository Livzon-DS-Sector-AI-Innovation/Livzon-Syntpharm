import { cache } from 'react'
import { cookies } from 'next/headers'
import { getMenuConfig } from '@/actions/menu'
import { getMyPermissions } from '@/lib/api/server/permission'
import { moduleMenus } from '@/lib/menu-config'
import { resolveMenus } from '@/lib/menu/resolve'
import {
  MODULE_ACCESS_PERMS,
  SUBMENU_ACCESS_PERMS,
  canAccess,
  type PermissionView,
} from '@/lib/permissions/modules'
import type { PermissionCode } from '@/lib/permissions/codes'

/** 当前请求用户的权限快照（未登录 / 后端不可用 → null）。 */
export interface PermissionsSnapshot {
  permissions: string[]
  isSuperuser: boolean
}

/**
 * 拉取当前请求用户的权限快照。失败返回 null（由调用方按 fail-closed 处理）。
 *
 * 使用 React.cache 做单请求级去重：同一次渲染/请求中多次调用只会发一次后端请求。
 */
export const getPermissionsSnapshot = cache(async (): Promise<PermissionsSnapshot | null> => {
  const token = (await cookies()).get('auth_token')?.value
  if (!token) return null

  try {
    const res = (await getMyPermissions(token)) as {
      data?: { permissions?: string[]; is_superuser?: boolean }
    }
    const data = res?.data
    if (!data) return null
    return {
      permissions: data.permissions ?? [],
      isSuperuser: Boolean(data.is_superuser),
    }
  } catch {
    // 后端不可用 / 权限未部署：视为拿不到权限
    return null
  }
})

/**
 * 服务端检查当前请求用户是否拥有某权限（超管直接放行）。
 *
 * 用在 RSC 页面里做**页面级**守卫 —— 相比客户端守卫没有 loading 闪烁：
 *
 *   if (!(await hasPermission(PERM.userRead))) return <NoAccessResult />
 *
 * 权限拉取失败时按「无权限」处理（fail-closed），与前端隐藏按钮的策略一致。
 */
export async function hasPermission(code: PermissionCode): Promise<boolean> {
  return hasAnyPermission([code])
}

/**
 * 拥有其中任意一个权限即通过。
 *
 * 用于「一个页面装多个 Tab、每个 Tab 各自有权限」的场景：只要有一个 Tab 有权，
 * 页面就该放行（具体 Tab 的可见性由客户端按权限过滤）。
 * 只拉一次 `my-permissions`，不会因为传多个权限码而多发请求。
 */
export async function hasAnyPermission(codes: readonly PermissionCode[]): Promise<boolean> {
  const snapshot = await getPermissionsSnapshot()
  if (!snapshot) return false
  if (snapshot.isSuperuser) return true
  const granted = new Set(snapshot.permissions)
  return codes.some((code) => granted.has(code))
}

/**
 * 当前用户可见的模块（供顶部导航 / 侧边栏渲染）。
 *
 * 规则见 `lib/permissions/modules.ts`：**未接入权限的模块恒可见**，
 * 因此即使权限接口不可用（snapshot 为 null），导航也不会整体消失 ——
 * 只有已接入权限控制的模块（当前 = 系统管理）会被隐藏。
 */
export async function getPermissionView(): Promise<PermissionView> {
  const snapshot = await getPermissionsSnapshot()
  const granted = new Set(snapshot?.permissions ?? [])
  const isSuperuser = snapshot?.isSuperuser ?? false

  // 菜单栏管理配置（显隐 / 权重 / 权限绑定 / 自定义项）：读不到按空配置 = 代码默认
  const menuConfig = await getMenuConfig()
  const modules = resolveMenus(menuConfig, granted, isSuperuser)

  return {
    visibleModuleKeys: modules.map((mod) => mod.key),
    granted: [...granted],
    isSuperuser,
    menuConfig,
  }
}

/**
 * 登录后的落地路径：按 `moduleMenus` 顺序取第一个「可见」模块的首页。
 * 一个都没有（所有模块都已接入且都无权限）→ 返回 null，由调用方渲染空态。
 */
export async function resolveLandingPath(): Promise<string | null> {
  const view = await getPermissionView()
  const visible = new Set(view.visibleModuleKeys)
  const granted = new Set(view.granted)
  const isSuperuser = view.isSuperuser

  for (const mod of moduleMenus) {
    if (!visible.has(mod.key)) continue
    // settings 模块根路径 `/settings` 需要 platform:config:read；只持后台其它权限（如
    // audit:read / user:read / ops:read）的账号会落到这里却看到「权限不足」。
    // 因此对 settings 特判：落到第一个「有权限」的子页面，而不是模块根。
    if (mod.key === 'settings') {
      const firstVisible = (mod.children ?? []).find((child) =>
        canAccess(granted, isSuperuser, SUBMENU_ACCESS_PERMS[child.key]),
      )
      if (firstVisible?.path) return firstVisible.path
    }
    return mod.path
  }
  return null
}

/**
 * 模块级页面守卫（供 `app/(dashboard)/<module>/layout.tsx` 使用）。
 *
 * 口径必须与 `MODULE_ACCESS_PERMS`（顶部导航准入）**严格一致**，否则会出现
 * 「导航有入口、点进去被拦」或「导航没有、URL 直连却能进」。
 *
 * - 未登记权限的模块 → 恒放行（未接入的模块不受影响）；
 * - 权限拉取失败 → 按无权限处理（fail-closed，与页面级守卫一致）。
 */
export async function hasModuleAccess(moduleKey: string): Promise<boolean> {
  const codes = MODULE_ACCESS_PERMS[moduleKey]
  if (!codes || codes.length === 0) return true
  return hasAnyPermission(codes)
}
