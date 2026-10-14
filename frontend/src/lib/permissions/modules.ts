import { PERM } from '@/lib/permissions/codes'
import type { PermissionCode } from '@/lib/permissions/codes'
import type { MenuConfigData } from '@/types/menu-admin'

/**
 * 模块准入权限表（**opt-in 白名单**，唯一权威）。
 *
 * 规则：
 * - 表里有该模块 → 该模块**已接入权限控制**：用户必须拥有列出的任一权限，
 *   顶部导航才显示这个模块的 Tab，模块页面才允许进入。
 * - 表里没有该模块 → **未接入权限管理的模块不受影响**：导航照旧显示、页面照旧可进，
 *   与接入权限之前的行为完全一致。
 *
 * 新增接入一个模块时改两处：
 * 1. 这里加一行（业务模块的权限码要在后端 registry 登记，见
 *    `backend/app/platform/permission/registry.py`）；
 * 2. 给该模块根目录加 `app/(dashboard)/<module>/layout.tsx` 页面级守卫
 *    （未接入的模块不要加，否则就会影响它）。
 */

/**
 * 模块 Tab 的准入权限（任一满足即可）。key 与 `lib/menu-config.ts` 的 module.key 对齐。
 *
 * 12 个业务模块统一用**模块访问码**（`<module>:module:read`，菜单级粗粒度）；
 * `settings`（首批接入）沿用各子页守卫口径的并集，见下方 SUBMENU_ACCESS_PERMS。
 */
export const MODULE_ACCESS_PERMS: Partial<Record<string, readonly PermissionCode[]>> = {
  production: [PERM.productionRead],
  equipment: [PERM.equipmentRead],
  safety: [PERM.safetyRead],
  environment: [PERM.environmentRead],
  energy: [PERM.energyRead],
  warehouse: [PERM.warehouseRead],
  procurement: [PERM.procurementRead],
  administration: [PERM.administrationRead],
  hr: [PERM.hrRead],
  research: [PERM.researchRead],
  registration: [PERM.registrationRead],
  quality: [PERM.qualityRead],
  // 系统管理（首批接入）：取各子页守卫口径的并集，见下方 SUBMENU_ACCESS_PERMS
  settings: [PERM.userRead, PERM.configRead, PERM.roleRead, PERM.opsRead, PERM.auditRead],
}

/**
 * 模块内子菜单的准入权限（未登记的菜单项不受影响）。
 *
 * 口径必须与对应页面的 RSC 守卫**严格一致**，否则会出现「看得到入口、点进去被拦」：
 * - settings-overview → app/(dashboard)/settings/page.tsx             （platform:config:read）
 * - users             → app/(dashboard)/settings/users/page.tsx       （platform:user:read）
 * - login-logs        → app/(dashboard)/settings/login-logs/page.tsx  （platform:audit:read）
 * - permission        → app/(dashboard)/settings/permission/page.tsx  （platform:role:read）
 * - ops               → app/(dashboard)/settings/ops/page.tsx         （platform:ops:read）
 */
export const SUBMENU_ACCESS_PERMS: Record<string, readonly PermissionCode[]> = {
  'settings-overview': [PERM.configRead],
  users: [PERM.userRead],
  'login-logs': [PERM.auditRead],
  audit: [PERM.auditRead],
  permission: [PERM.roleRead],
  ops: [PERM.opsRead],
  'settings-menus': [PERM.opsRead],
}

/** 服务端（RSC layout）下发给客户端导航的权限视图。 */
export interface PermissionView {
  /** 当前用户可见的模块 key（已按菜单权重排序；未接入权限的模块恒在其中） */
  visibleModuleKeys: string[]
  /** 当前用户持有的权限码 */
  granted: string[]
  isSuperuser: boolean
  /** 菜单栏管理配置（显隐 / 权重 / 权限绑定 / 自定义菜单项）；未配置为空 */
  menuConfig: MenuConfigData
}

/**
 * 通用判定：`codes` 未登记（undefined / 空数组）→ 直接放行（未接入不受影响）。
 *
 * 允许传入 `string[]`：菜单配置里可填写尚未登记的业务权限码（如 `quality:module:read`）。
 */
export function canAccess(
  granted: ReadonlySet<string>,
  isSuperuser: boolean,
  codes?: readonly string[],
): boolean {
  if (!codes || codes.length === 0) return true
  if (isSuperuser) return true
  return codes.some((code) => granted.has(code))
}

/** 能否进入某个模块（未登记 → 可以）。 */
export function canEnterModule(
  granted: ReadonlySet<string>,
  isSuperuser: boolean,
  moduleKey: string,
): boolean {
  return canAccess(granted, isSuperuser, MODULE_ACCESS_PERMS[moduleKey])
}

/** 子菜单项是否可见（未登记 → 可见）。 */
export function canSeeMenuItem(
  granted: ReadonlySet<string>,
  isSuperuser: boolean,
  menuKey: string,
): boolean {
  return canAccess(granted, isSuperuser, SUBMENU_ACCESS_PERMS[menuKey])
}
