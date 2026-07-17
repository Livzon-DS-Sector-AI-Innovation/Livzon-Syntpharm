'use client'
"use client"

import { usePathname, useRouter, useSearchParams } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import { Menu } from "antd"
import type { MenuProps } from "antd"
import { getModuleByKey } from "@/lib/menu-config"
import { usePermission } from "@/hooks/usePermission"
import type { SubMenuItem } from "@/lib/menu-config"
import { fetchWarehouseFeishuTablesByParams } from "@/lib/api/client/warehouse"
import type { WarehouseFeishuBusinessDomain, WarehouseFeishuTable } from "@/types/warehouse"
import { SettingOutlined } from "@ant-design/icons"
import { useSidebarStore } from "@/stores/sidebar"
import { getCurrentUser } from "@/actions/auth"
import type { User } from "@/types/user"

type MenuItem = Required<MenuProps>['items'][number]

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

function buildMenuItems(items: SubMenuItem[]): MenuItem[] {
  return items.map((item) => {
    if (item.children && item.children.length > 0) {
      return {
        key: item.key,
        label: item.label,
        children: buildMenuItems(item.children),
      }
    }
    const leaf: MenuItem = { key: item.key, label: item.label }
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

function findSelectedKey(
  items: SubMenuItem[],
  pathname: string,
  query: URLSearchParams,
): string | undefined {
  const leaves = collectLeaves(items)
  const sorted = leaves.sort((a, b) => b.path.length - a.path.length)
  const match = sorted.find((item) => matchesMenuPath(item.path, pathname, query))
  return match?.key
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
}

export function Sidebar({ onNavigate }: SidebarProps) {
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const { collapsed } = useSidebarStore()
  const router = useRouter()
  const { user: currentUser } = usePermission()
  const moduleKey = pathname.split("/")[1] || "production"
  const currentModule = getModuleByKey(moduleKey)
  const [user, setUser] = useState<User | null>(null)
  const [warehouseTables, setWarehouseTables] = useState<WarehouseFeishuTable[]>([])
  const queryString = searchParams.toString()
  const query = useMemo(() => new URLSearchParams(queryString), [queryString])

  useEffect(() => {
    getCurrentUser().then(setUser)
  }, [])

  useEffect(() => {
    if (moduleKey !== "warehouse") {
      return
    }

    let cancelled = false
    fetchWarehouseFeishuTablesByParams({ enabled: true })
      .then((tables) => {
        if (cancelled) return
        setWarehouseTables(tables)
      })
      .catch(() => {
        if (!cancelled) setWarehouseTables([])
      })

    return () => {
      cancelled = true
    }
  }, [moduleKey])

  const moduleChildren = useMemo(() => {
    if (!currentModule) return []
    const filtered = currentModule.children
    if (moduleKey !== "warehouse") return filtered
    return withWarehouseTables(filtered, warehouseTables)
  }, [currentModule, moduleKey, warehouseTables])

  const menuItems = buildMenuItems(moduleChildren)
  const keyPathMap = buildKeyPathMap(moduleChildren)
  const selectedKey = currentModule
    ? findSelectedKey(moduleChildren, pathname, query)
    : undefined

  const [openKeys, setOpenKeys] = useState<string[]>(() =>
    currentModule ? collectAncestorKeys(moduleChildren, pathname, query) : []
  )

  useEffect(() => {
    if (currentModule) {
      const ancestorKeys = collectAncestorKeys(moduleChildren, pathname, query)
      if (ancestorKeys.length > 0) {
        setOpenKeys((current) => Array.from(new Set([...current, ...ancestorKeys])))
      }
    }
  }, [currentModule, moduleChildren, pathname, query])

  const handleOpenChange = (keys: string[]) => {
    setOpenKeys(keys)
  }

  const handleClick: MenuProps['onClick'] = ({ key }) => {
    const path = keyPathMap.get(key)
    if (path) {
      router.push(path)
      onNavigate?.()
    }
  }

  if (!currentModule) return null

  return (
    <aside
      className={`bg-[var(--color-canvas)] border-r border-[var(--color-hairline)] flex flex-col shrink-0 overflow-hidden transition-all duration-200 ${
        collapsed ? "w-0 border-r-0" : "w-56"
      }`}
    >
      <div className="flex-1 overflow-y-auto min-w-[224px]">
        <div
          className={`px-4 pt-5 pb-3${moduleKey === "safety" ? " cursor-pointer group" : ""}`}
          onClick={moduleKey === "safety" ? () => router.push(currentModule.path) : undefined}
        >
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
        <button
          onClick={() => router.push("/settings")}
          className="text-[var(--color-stone)] hover:text-[var(--color-primary)] transition-colors cursor-pointer"
          title="系统设置"
        >
          <SettingOutlined style={{ fontSize: 16 }} />
        </button>
      </div>
    </aside>
  )
}
