import { moduleMenus, type SubMenuItem } from '@/lib/menu-config'
import { MODULE_ACCESS_PERMS, SUBMENU_ACCESS_PERMS, canAccess } from '@/lib/permissions/modules'
import type { MenuConfigData } from '@/types/menu-admin'

/**
 * 菜单树解析：把「代码里的菜单结构」与「数据库里的菜单配置」合并，
 * 产出**该用户可见**且**按权重排序**的菜单树（含管理员自定义菜单项）。
 *
 * 规则（与 `lib/permissions/modules.ts` 的默认值协同）：
 * - 未配置的菜单项 → 沿用代码默认（权限规则、原顺序）→ 既有行为不变；
 * - 权重：数字小排前面；未配置时按代码顺序生成（10/20/30…），同权重按代码顺序稳定；
 * - 权限：显式配 `[]` = 不限制；配了权限码 = 任一满足即可；超管拥有全部权限；
 * - **显隐：配置为 `visible: false` 即隐藏，对所有人（含超管）生效** —— 否则超管
 *   打开「菜单管理」关掉某项后，自己仍能看到，会误判「开关没生效」。
 *   唯一例外是 `PROTECTED_MENU_KEYS`（后端护栏同样禁止隐藏），防管理员自锁；
 * - 自定义菜单项：`parent === null` 为模块级（顶部一个 Tab），否则挂在对应父菜单下。
 */

const DEFAULT_SORT_STEP = 10
/** 自定义项的默认权重：排在已配置项之后 */
export const CUSTOM_DEFAULT_SORT = 999

/**
 * 系统保护项：**始终可见**，与后端 `menu_service.PROTECTED_MENU_KEYS` 保持一致。
 * 目的：管理员把所有菜单都关掉后，仍能进入「系统设置 / 菜单管理」把配置改回来。
 */
export const PROTECTED_MENU_KEYS = new Set(['settings', 'settings-overview', 'settings-menus'])

export interface ResolvedModule {
  key: string
  label: string
  icon: string
  path: string
  isCustom: boolean
  children: SubMenuItem[]
}

type SortableChild = SubMenuItem & { __sort: number; __order: number }

function resolveSort(config: MenuConfigData, key: string, fallback: number): number {
  const value = config.items[key]?.sort
  return typeof value === 'number' ? value : fallback
}

function isVisible(config: MenuConfigData, key: string): boolean {
  // 保护项始终可见（后端校验也会拒绝隐藏它们），避免管理员把自己锁在门外
  if (PROTECTED_MENU_KEYS.has(key)) return true
  return config.items[key]?.visible !== false
}

/** 生效菜单名：配置里有非空覆盖就用覆盖值，否则用代码默认名 */
function resolveLabel(config: MenuConfigData, key: string, fallback: string): string {
  const value = config.items[key]?.label
  return typeof value === 'string' && value.trim() ? value : fallback
}

/** 生效权限要求：未配置（null/undefined）→ 代码默认；显式 `[]` → 不限制 */
function resolvePerms(
  config: MenuConfigData,
  key: string,
  defaults?: readonly string[],
): readonly string[] | undefined {
  const configured = config.items[key]?.perms
  if (configured == null) return defaults
  return configured.length > 0 ? configured : undefined
}

function filterChildren(
  items: SubMenuItem[],
  parentKey: string,
  config: MenuConfigData,
  granted: ReadonlySet<string>,
  isSuperuser: boolean,
): SubMenuItem[] {
  const kept: SortableChild[] = []

  items.forEach((item, index) => {
    const perms = resolvePerms(config, item.key, SUBMENU_ACCESS_PERMS[item.key])
    if (!canAccess(granted, isSuperuser, perms)) return
    if (!isVisible(config, item.key)) return

    let children: SubMenuItem[] | undefined
    if (item.children && item.children.length > 0) {
      children = filterChildren(item.children, item.key, config, granted, isSuperuser)
      if (children.length === 0) return // 子项全被过滤 → 父分组不显示
    }

    kept.push({
      ...item,
      label: resolveLabel(config, item.key, item.label),
      children,
      __sort: resolveSort(config, item.key, (index + 1) * DEFAULT_SORT_STEP),
      __order: index,
    })
  })

  const custom: SortableChild[] = config.custom
    .filter((c) => c.parent === parentKey)
    .filter((c) => c.visible)
    .filter((c) => canAccess(granted, isSuperuser, c.perms.length > 0 ? c.perms : undefined))
    .map((c, index) => ({
      key: c.id,
      label: c.title,
      path: c.path,
      __sort: c.sort,
      __order: 1000 + index,
    }))

  return [...kept, ...custom]
    .sort((a, b) => a.__sort - b.__sort || a.__order - b.__order)
    .map(({ __sort, __order, ...rest }) => {
      void __sort
      void __order
      return rest as SubMenuItem
    })
}

/**
 * 解析出该用户可见的模块列表（含自定义模块级项），已按权重排序；
 * 每个模块的 `children` 也已过滤 + 排序 + 并入自定义子项。
 */
export function resolveMenus(
  config: MenuConfigData,
  granted: ReadonlySet<string>,
  isSuperuser: boolean,
): ResolvedModule[] {
  const modules: Array<ResolvedModule & { __sort: number; __order: number }> = []

  moduleMenus.forEach((mod, index) => {
    const perms = resolvePerms(config, mod.key, MODULE_ACCESS_PERMS[mod.key])
    if (!canAccess(granted, isSuperuser, perms)) return
    if (!isVisible(config, mod.key)) return

    const children = filterChildren(mod.children, mod.key, config, granted, isSuperuser)
    // 模块下原本有子菜单、但被隐藏或权限过滤后一个不剩 → 模块 Tab 也一并隐藏，
    // 避免顶部留一个点进去空空如也的模块（保护项不会走到这里）
    if (mod.children.length > 0 && children.length === 0) return

    modules.push({
      key: mod.key,
      label: resolveLabel(config, mod.key, mod.label),
      icon: mod.icon,
      path: mod.path,
      isCustom: false,
      children,
      __sort: resolveSort(config, mod.key, (index + 1) * DEFAULT_SORT_STEP),
      __order: index,
    })
  })

  const customModules: Array<ResolvedModule & { __sort: number; __order: number }> = config.custom
    .filter((c) => c.parent === null)
    .filter((c) => c.visible)
    .filter((c) => canAccess(granted, isSuperuser, c.perms.length > 0 ? c.perms : undefined))
    .map((c, index) => ({
      key: c.id,
      label: c.title,
      icon: c.icon,
      path: c.path,
      isCustom: true,
      children: filterChildren([], c.id, config, granted, isSuperuser),
      __sort: c.sort,
      __order: 1000 + index,
    }))

  return [...modules, ...customModules]
    .sort((a, b) => a.__sort - b.__sort || a.__order - b.__order)
    .map(({ __sort, __order, ...rest }) => {
      void __sort
      void __order
      return rest
    })
}
