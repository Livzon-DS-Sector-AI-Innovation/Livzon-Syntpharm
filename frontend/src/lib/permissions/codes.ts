/**
 * 平台权限码常量（与后端 app/platform/permission/registry.py 的 PLATFORM_PERMISSIONS 对齐）。
 *
 * 为什么要用常量：写错权限码在编译期就能发现（`can()` 的参数是联合类型），
 * 而不是运行到点击按钮时才静默失效。
 *
 * 新增权限码时**两边都要改**：后端 registry + 这里。
 */

/**
 * 业务模块访问码（**菜单级**：每个模块 1 个）。
 *
 * 与后端 `BUSINESS_MODULE_PERMISSIONS`（由 `BUSINESS_MODULES` 生成）一一对应：
 * `<module>:module:read`。只控制「模块菜单是否可见 + 模块页面能否进入」；
 * 具体接口权限（`<module>:<resource>:<action>`）后续按需追加，两层正交。
 */
export const MODULE_PERM = {
  productionRead: 'production:module:read',
  equipmentRead: 'equipment:module:read',
  safetyRead: 'safety:module:read',
  environmentRead: 'environment:module:read',
  energyRead: 'energy:module:read',
  warehouseRead: 'warehouse:module:read',
  procurementRead: 'procurement:module:read',
  administrationRead: 'administration:module:read',
  hrRead: 'hr:module:read',
  researchRead: 'research:module:read',
  registrationRead: 'registration:module:read',
  qualityRead: 'quality:module:read',
} as const

export const PERM = {
  userRead: 'platform:user:read',
  userManage: 'platform:user:manage',
  roleRead: 'platform:role:read',
  roleManage: 'platform:role:manage',
  permissionRead: 'platform:permission:read',
  apiBindingRead: 'platform:api-binding:read',
  grantRead: 'platform:grant:read',
  grantManage: 'platform:grant:manage',
  auditRead: 'platform:audit:read',
  configRead: 'platform:config:read',
  configManage: 'platform:config:manage',
  opsRead: 'platform:ops:read',
  opsManage: 'platform:ops:manage',
  ...MODULE_PERM,
} as const

export type PermissionCode = (typeof PERM)[keyof typeof PERM]

/** 平台全部权限码（供校验脚本比对后端 registry 用） */
export const ALL_PERMISSION_CODES: readonly string[] = Object.values(PERM)

// ── 统一文案 ───────────────────────────────────────────────────────
// 无权限时给"权限不足"的提示，而不是把 403 这种技术状态码抛给用户

export const PERMISSION_DENIED_TITLE = '当前用户权限不足'
export const PERMISSION_DENIED_HINT = '请联系管理员为你的账号分配相应权限'
