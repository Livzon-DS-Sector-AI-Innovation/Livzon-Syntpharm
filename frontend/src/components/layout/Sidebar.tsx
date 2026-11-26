'use client'

import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useMemo, useState } from "react"
import type { ReactNode } from "react"
import { useQuery } from "@tanstack/react-query"
import { Menu } from "antd"
import type { MenuProps } from "antd"
import type { SubMenuItem } from "@/lib/menu-config"
import type { ResolvedModule } from "@/lib/menu/resolve"
import type { PermissionView } from "@/lib/permissions/modules"
import { fetchWarehouseFeishuTablesByParams } from "@/lib/api/client/warehouse"
import type { WarehouseFeishuBusinessDomain, WarehouseFeishuTable } from "@/types/warehouse"
import { HomeOutlined, IdcardOutlined, SettingOutlined } from "@ant-design/icons"
import { ModuleIcon } from "@/components/Icons"
import { useSidebarStore } from "@/stores/sidebar"
import { MenuLockLabel } from "./MenuLockLabel"

type MenuItem = Required<MenuProps>['items'][number]

/**
 * 不属于任何业务模块的独立页面（/home、/profile）：
 * 仍渲染简化的侧栏骨架，避免内容区宽度跳变。
 */
const SIMPLE_PAGES: Record<
  string,
  { title: string; icon: ReactNode; selectedKey: string; path: string; items: MenuItem[] }
> = {
  home: {
    title: "首页",
    icon: <HomeOutlined />,
    selectedKey: "home",
    path: "/home",
    items: [{ key: "home", label: "工作台", icon: <HomeOutlined /> }],
  },
  profile: {
    title: "个人中心",
    icon: <IdcardOutlined />,
    selectedKey: "profile",
    path: "/profile",
    items: [{ key: "profile", label: "个人信息", icon: <IdcardOutlined /> }],
  },
}

const warehouseDomainMeta: Record<
  WarehouseFeishuBusinessDomain,
  { menuKey: string; routeSegment: string }
> = {
  finished_product: { menuKey: "raw-material", routeSegment: "raw-material" },
  materials_packaging: { menuKey: "packaging", routeSegment: "packaging" },
  hardware: { menuKey: "product", routeSegment: "product" },
}

function buildWarehouseTablePath(table: WarehouseFeishuTable): string | null {
  const meta = warehouseDomainMeta[table.business_domain]
  if (!meta || !table.id) return null
  const params = new URLSearchParams({ table_id: table.id })
  return `/warehouse/${meta.routeSegment}?${params.toString()}`
}

function buildWarehouseTableLabel(table: WarehouseFeishuTable): string {
  return `${table.name}（${table.record_count || 0} 条）`
}

function withWarehouseTables(
  items: SubMenuItem[],
  tables: WarehouseFeishuTable[],
): SubMenuItem[] {
  const tablesByMenuKey = tables.reduce<Record<string, SubMenuItem[]>>((acc, table) => {
    const meta = warehouseDomainMeta[table.business_domain]
    const path = buildWarehouseTablePath(table)
    if (!meta || !path || !table.id) return acc

    acc[meta.menuKey] = [
      ...(acc[meta.menuKey] || []),
      {
        key: `${meta.menuKey}-table-${table.id}`,
        label: buildWarehouseTableLabel(table),
        path,
      },
    ]
    return acc
  }, {})

  return items.map((item) => {
    const tableItems = tablesByMenuKey[item.key]
    if (!tableItems?.length) return item

    return {
      ...item,
      path: "",
      children: tableItems,
    }
  })
}

function parseMenuPath(path: string): { pathname: string; query: URLSearchParams } {
  const [pathname, queryString = ""] = path.split("?")
  return { pathname, query: new URLSearchParams(queryString) }
}

function queryContains(current: URLSearchParams, expected: URLSearchParams): boolean {
  for (const [key, value] of expected.entries()) {
    if (current.get(key) !== value) return false
  }
  return true
}

function matchesMenuPath(itemPath: string, pathname: string, query: URLSearchParams): boolean {
  const parsed = parseMenuPath(itemPath)
  if (parsed.query.size > 0) {
    return pathname === parsed.pathname && queryContains(query, parsed.query)
  }
  return pathname === parsed.pathname || pathname.startsWith(parsed.pathname + "/")
}

function buildKeyPathMap(items: SubMenuItem[]): Map<string, string> {
  const map = new Map<string, string>()
  for (const item of items) {
    if (item.children && item.children.length > 0) {
      const childMap = buildKeyPathMap(item.children)
      childMap.forEach((v, k) => map.set(k, v))
    } else if (item.path) {
      map.set(item.key, item.path)
    }
  }
  return map
}

/**
 * 菜单标签：
 * - `noAccess`（无权限）→ 灰显 + 锁图标，**仍可点击**（点击后由模块 layout 守卫渲染无权限页）
 * - `disabled`（未开发）→ 由 Antd Menu 的 disabled 处理，灰显且不可点
 */
function renderMenuLabel(label: string, noAccess?: boolean) {
  if (!noAccess) return label
  return (
    <span className="opacity-55">
      <MenuLockLabel label={label} />
    </span>
  )
}

function buildMenuItems(
  items: SubMenuItem[],
  onNavigateToPath: (path: string) => void,
): MenuItem[] {
  return items.map((item): MenuItem => {
    const label = renderMenuLabel(item.label, item.noAccess)
    if (item.children && item.children.length > 0) {
      const children = buildMenuItems(item.children, onNavigateToPath)
      const parentPath = item.path
      // 有 children 又有 path 的父节点：点标题直接进看盘页，箭头仍可展开/收起
      if (parentPath) {
        return {
          key: item.key,
          label,
          children,
          onTitleClick: () => onNavigateToPath(parentPath),
        }
      }
      return {
        key: item.key,
        label,
        children,
      }
    }
    const leaf: MenuItem = { key: item.key, label }
    if (item.disabled) {
      leaf.disabled = true
    }
    return leaf
  })
}

function collectLeaves(items: SubMenuItem[]): SubMenuItem[] {
  return items.flatMap((item) => {
    if (item.children && item.children.length > 0) {
      return collectLeaves(item.children)
    }
    if (item.disabled || !item.path) return []
    return [item]
  })
}

/** 子菜单的过滤 + 排序 + 自定义项合并，统一由 `resolveMenus` 完成（见 lib/menu/resolve.ts）。 */

/** 自身带 path 的父节点（如「偏差管理」）：父节点也可能是落地页 */
function collectParentsWithPath(items: SubMenuItem[]): SubMenuItem[] {
  return items.flatMap((item) => {
    if (item.children && item.children.length > 0) {
      const self = item.path && !item.disabled ? [item] : []
      return [...self, ...collectParentsWithPath(item.children)]
    }
    return []
  })
}

function findSelectedKey(
  items: SubMenuItem[],
  pathname: string,
  query: URLSearchParams,
): string | undefined {
  const leaves = collectLeaves(items)
  const sorted = leaves.sort((a, b) => b.path.length - a.path.length)
  const match = sorted.find((item) => matchesMenuPath(item.path, pathname, query))
  if (match) return match.key
  // 父节点只做精确匹配，避免父路径前缀抢走子页面的选中态
  const parent = collectParentsWithPath(items).find(
    (item) => parseMenuPath(item.path).pathname === pathname,
  )
  return parent?.key
}

function collectAncestorKeys(
  items: SubMenuItem[],
  pathname: string,
  query: URLSearchParams,
): string[] {
  for (const item of items) {
    if (item.children && item.children.length > 0) {
      if (containsPath(item.children, pathname, query)) {
        return [item.key, ...collectAncestorKeys(item.children, pathname, query)]
      }
      // 命中父节点自身的落地页：展开该父节点，让同级入口可见
      if (item.path && parseMenuPath(item.path).pathname === pathname) {
        return [item.key]
      }
    }
  }
  return []
}

function containsPath(
  items: SubMenuItem[],
  pathname: string,
  query: URLSearchParams,
): boolean {
  for (const item of items) {
    if (item.children && item.children.length > 0) {
      if (containsPath(item.children, pathname, query)) return true
    } else if (!item.disabled && item.path && matchesMenuPath(item.path, pathname, query)) {
      return true
    }
  }
  return false
}

interface SidebarProps {
  onNavigate?: () => void
  /** 移动端抽屉内使用：强制展开，忽略桌面折叠状态 */
  forceExpanded?: boolean
  permissionView: PermissionView
  /** 由 AppShell 统一解析的菜单树（桌面侧栏与移动抽屉共用，避免重复计算） */
  menus: ResolvedModule[]
  /** 菜单 key → 外部系统地址：命中时点击在新标签页打开，未配置时走原有本地路由 */
  externalLinks?: Record<string, string>
}

export function Sidebar({
  onNavigate,
  forceExpanded = false,
  permissionView,
  menus,
  externalLinks = {},
}: SidebarProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { collapsed: collapsedState } = useSidebarStore()
  const collapsed = collapsedState && !forceExpanded
  const router = useRouter()
  const moduleKey = pathname.split("/")[1] || "production"
  // 仓储模块的飞书表菜单项：只有进到 warehouse 才拉，交给 React Query 管缓存与去重
  const { data: warehouseTablesData } = useQuery({
    queryKey: ["warehouse-feishu-tables"],
    queryFn: () => fetchWarehouseFeishuTablesByParams({ enabled: true }),
    enabled: moduleKey === "warehouse",
  })
  const warehouseTables: WarehouseFeishuTable[] = useMemo(
    () => warehouseTablesData ?? [],
    [warehouseTablesData],
  )
  const queryString = searchParams.toString()
  const query = useMemo(() => new URLSearchParams(queryString), [queryString])
  // 菜单树 = 代码结构 + 服务端下发的菜单配置（显隐 / 权重 / 权限 / 自定义项），已在 AppShell 解析
  const currentModule = menus.find((mod) => mod.key === moduleKey)

  const moduleChildren = useMemo(() => {
    if (!currentModule) return []
    return moduleKey === "warehouse"
      ? withWarehouseTables(currentModule.children, warehouseTables)
      : currentModule.children
  }, [currentModule, moduleKey, warehouseTables])

  const navigateToPath = (path: string) => {
    router.push(path)
    onNavigate?.()
  }

  const menuItems = buildMenuItems(moduleChildren, navigateToPath)
  const keyPathMap = buildKeyPathMap(moduleChildren)
  const selectedKey = currentModule
    ? findSelectedKey(moduleChildren, pathname, query)
    : undefined

  const [openKeys, setOpenKeys] = useState<string[]>(() =>
    currentModule ? collectAncestorKeys(moduleChildren, pathname, query) : []
  )

  // Sync openKeys when navigation changes (adjusting state during render)
  const [prevNavKey, setPrevNavKey] = useState<string>('')
  // 用模块 key 拼导航指纹：以前直接把 currentModule 对象插进模板串，得到的是 "[object Object]"，
  // 换模块时指纹不变，上一模块的展开项会被带到新模块。
  const navKey = currentModule ? `${currentModule.key}|${pathname}|${queryString}` : ''
  if (navKey !== prevNavKey && currentModule) {
    setPrevNavKey(navKey)
    const ancestorKeys = collectAncestorKeys(moduleChildren, pathname, query)
    if (ancestorKeys.length > 0) {
      setOpenKeys((current) => Array.from(new Set([...current, ...ancestorKeys])))
    }
  }

  const handleOpenChange = (keys: string[]) => {
    setOpenKeys(keys)
  }

  const handleClick: MenuProps['onClick'] = ({ key }) => {
    // 配置了外部系统地址的菜单项：新标签页打开，本系统页面不跳走；
    // 未配置时保持原有本地路由跳转，选中态逻辑不受影响。
    const externalUrl = externalLinks[key]
    if (externalUrl) {
      window.open(externalUrl, '_blank', 'noopener,noreferrer')
      onNavigate?.()
      return
    }
    const path = keyPathMap.get(key)
    if (path) {
      navigateToPath(path)
    }
  }

  // 首页 / 个人中心不属于任何业务模块：渲染简化侧栏，避免内容区宽度跳变
  if (!currentModule) {
    const simple = SIMPLE_PAGES[moduleKey]
    if (!simple) return null
    return (
      <aside
        className={`bg-[var(--color-canvas)] border-r border-[var(--color-hairline)] flex flex-col shrink-0 overflow-hidden transition-all duration-200 ${
          collapsed ? "w-0 border-r-0" : "w-56"
        }`}
      >
        <div className="flex-1 overflow-y-auto min-w-[224px]">
          <div className="px-4 pt-5 pb-3 flex items-center gap-2">
            <span className="shrink-0 text-[18px] text-[var(--color-steel)]">
              {simple.icon}
            </span>
            <h2 className="text-[18px] font-semibold text-[var(--color-charcoal)]">
              {simple.title}
            </h2>
          </div>
          <Menu
            mode="inline"
            selectedKeys={[simple.selectedKey]}
            items={simple.items}
            onClick={() => {
              router.push(simple.path)
              onNavigate?.()
            }}
            className="sidebar-menu"
            style={{ borderInlineEnd: "none" }}
          />
        </div>
        <div className="px-4 py-3 border-t border-[var(--color-hairline-soft)]">
          <p className="text-[12px] text-[var(--color-stone)]">v0.1.1</p>
        </div>
      </aside>
    )
  }

  return (
    <aside
      className={`bg-[var(--color-canvas)] border-r border-[var(--color-hairline)] flex flex-col shrink-0 overflow-hidden transition-all duration-200 ${
        collapsed ? "w-0 border-r-0" : "w-56"
      }`}
    >
      <div className="flex-1 overflow-y-auto min-w-[224px]">
        <div
          className={`px-4 pt-5 pb-3 flex items-center gap-2${
            moduleKey === "safety" ? " cursor-pointer group" : ""
          }`}
          onClick={moduleKey === "safety" ? () => router.push(currentModule.path) : undefined}
        >
          <span
            className={`shrink-0 text-[var(--color-steel)]${
              moduleKey === "safety" ? " group-hover:text-[var(--color-primary)] transition-colors" : ""
            }`}
          >
            <ModuleIcon name={currentModule.icon} className="w-[18px] h-[18px]" />
          </span>
          <h2
            className={`text-[18px] font-semibold text-[var(--color-charcoal)]${
              moduleKey === "safety" ? " group-hover:text-[var(--color-primary)] transition-colors" : ""
            }`}
          >
            {currentModule.label}
          </h2>
        </div>

        <Menu
          mode="inline"
          selectedKeys={selectedKey ? [selectedKey] : []}
          openKeys={openKeys}
          onOpenChange={handleOpenChange}
          items={menuItems}
          onClick={handleClick}
          className="sidebar-menu"
          style={{ borderInlineEnd: 'none' }}
        />
      </div>

      <div className="px-4 py-3 border-t border-[var(--color-hairline-soft)] flex items-center justify-between">
        <p className="text-[12px] text-[var(--color-stone)]">
          v0.1.1
        </p>
        {permissionView.visibleModuleKeys.includes("settings") && (
          <button
            onClick={() => router.push("/settings")}
            className="text-[var(--color-stone)] hover:text-[var(--color-primary)] transition-colors cursor-pointer"
            title="系统设置"
          >
            <SettingOutlined style={{ fontSize: 16 }} />
          </button>
        )}
      </div>
    </aside>
  )
}
