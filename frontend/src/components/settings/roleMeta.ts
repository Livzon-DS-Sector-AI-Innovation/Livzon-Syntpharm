/**
 * 角色类型 → 中文名 + 标签色。
 *
 * 「模块配置 · 权限管理」「按人查权限」两处都要显示角色类型，
 * 以前各自维护一份文案（模块页还漏了 `system`），统一到这里避免继续漂移。
 */
export const ROLE_TYPE_META: Record<string, { text: string; color: string }> = {
  system: { text: '系统管理员', color: 'red' },
  head: { text: '模块负责人', color: 'gold' },
  manager: { text: '模块管理员', color: 'blue' },
  job: { text: '岗位角色', color: 'green' },
}

/**
 * 内置管理角色：由代码随权限注册表生成，页面只读。
 * 模块配置页不可手工编辑，指派/移除由系统管理员在「系统管理 → 权限管理」完成。
 */
export const READONLY_ROLE_TYPES: ReadonlySet<string> = new Set(['system', 'head', 'manager'])
