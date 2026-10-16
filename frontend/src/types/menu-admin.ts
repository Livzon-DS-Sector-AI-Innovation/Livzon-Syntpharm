/**
 * 菜单栏管理（L1 显隐 / L2 权重 / L3 权限绑定 / L4 自定义菜单项）类型。
 *
 * 与后端 `app/platform/system/menu_schemas.py` 对应；配置存在
 * `core.module_settings`（module=menu, key=CONFIG），未配置时前端按代码默认渲染。
 */

export interface MenuItemOverride {
  /** 菜单显示名覆盖；null/空 = 按代码默认（菜单管理里可改） */
  label?: string | null
  visible?: boolean | null
  sort?: number | null
  perms?: string[] | null
}

export interface CustomMenuItem {
  id: string
  /** null = 模块级（顶部一个 Tab）；否则为父菜单 key */
  parent: string | null
  title: string
  path: string
  icon: string
  sort: number
  perms: string[]
  visible: boolean
}

export interface MenuConfigData {
  items: Record<string, MenuItemOverride>
  custom: CustomMenuItem[]
  updated_at?: string | null
}

export const EMPTY_MENU_CONFIG: MenuConfigData = { items: {}, custom: [] }
