/**
 * 角色类型 → 中文名 + 标签色。
 *
 * 「模块配置 · 权限管理」「按人查权限」两处都要显示角色类型，
 * 以前各自维护一份文案（模块页还漏了 `system`），统一到这里避免继续漂移。
 */
export const ROLE_TYPE_META: Record<string, { text: string; color: string }> = {
  system: { text: '系统管理员', color: 'red' },
  owner: { text: '模块负责人', color: 'gold' },
  delegate: { text: '模块代表', color: 'blue' },
  job: { text: '岗位角色', color: 'green' },
  // 历史值兜底：后端已退役并过滤 head/manager（迁移 0203 + 启动同步）。
  // 仍保留映射，避免「前端先发、后端/迁移未就绪」的窗口期页面失配。
  head: { text: '模块负责人', color: 'gold' },
  manager: { text: '模块代表', color: 'blue' },
}

/**
 * 内置管理角色：由代码随权限注册表生成，页面只读。
 * 模块负责人由系统管理员在「系统管理 → 权限管理」指派；
 * 模块代表由模块负责人在模块配置页指派。
 */
export const READONLY_ROLE_TYPES: ReadonlySet<string> = new Set(['system', 'owner', 'delegate', 'head', 'manager'])

/** 模块负责人（含旧值兼容）。 */
export function isOwnerRoleType(roleType: string | null | undefined): boolean {
  return roleType === 'owner' || roleType === 'head'
}

/** 模块代表（含旧值兼容）。 */
export function isDelegateRoleType(roleType: string | null | undefined): boolean {
  return roleType === 'delegate' || roleType === 'manager'
}