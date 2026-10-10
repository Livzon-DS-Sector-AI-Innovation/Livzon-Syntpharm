'use client'
"use client"

import { useState, useEffect } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { Dropdown, Avatar } from "antd"
import { LogoutOutlined, UserOutlined, MenuOutlined, MenuUnfoldOutlined, MenuFoldOutlined } from "@ant-design/icons"
import { moduleMenus } from "@/lib/menu-config"
import { ModuleIcon, SearchIcon, BellIcon } from "@/components/Icons"
import { logout, getCurrentUser } from "@/actions/auth"
import type { User, ImpersonateUserInfo } from "@/types/user"
import { usePermission } from "@/hooks/usePermission"
import { useSidebarStore } from "@/stores/sidebar"

interface ImpersonationStatus {
  is_impersonating: boolean
  original_user?: ImpersonateUserInfo
  impersonated_user?: ImpersonateUserInfo
}

async function getImpersonationStatus(): Promise<ImpersonationStatus | null> {
  return null
}

interface TopNavProps {
  onMenuClick?: () => void
}

export function TopNav({ onMenuClick }: TopNavProps) {
  const pathname = usePathname()
  const activeModule = pathname.split("/")[1] || "production"
  const [loggingOut, setLoggingOut] = useState(false)
  const [user, setUser] = useState<User | null>(null)
  const { loading } = usePermission()
  const isLoaded = !loading
  const { collapsed, toggle: toggleSidebar } = useSidebarStore()

  const [_impersonation, setImpersonation] = useState<ImpersonationStatus | null>(null)

  useEffect(() => {
    getCurrentUser().then(setUser)
    getImpersonationStatus().then(setImpersonation)
  }, [isLoaded])

  const handleLogout = async () => {
    setLoggingOut(true)
    try {
      await logout()
    } catch {
      // redirect() throws NEXT_REDIRECT, which Next.js handles internally
    }
  }

  const avatarSrc = user?.avatar_url || undefined
  const displayName = user?.name || "未登录"

  const _visibleMenus = moduleMenus

  return (
    <header className="h-16 bg-[var(--color-canvas)] border-b border-[var(--color-hairline)] flex items-center px-5 shrink-0">
      {/* Mobile menu button */}
      <button
        onClick={onMenuClick}
        className="w-8 h-8 flex items-center justify-center rounded-[var(--rounded-sm)] text-[var(--color-steel)] hover:text-[var(--color-charcoal)] hover:bg-[var(--color-surface)] transition-colors mr-2 md:hidden"
      >
        <MenuOutlined style={{ fontSize: 18 }} />
      </button>

      {/* Logo */}
      <div className="flex items-center gap-2.5 mr-6 shrink-0">
        <div className="w-7 h-7 rounded-[var(--rounded-md)] bg-[var(--color-primary)] flex items-center justify-center">
          <span className="text-white text-xs font-semibold">API</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[var(--color-charcoal)] text-[15px] font-semibold tracking-tight leading-tight">
            原料药
          </span>
          <span className="text-[var(--color-steel)] text-[11px] leading-tight hidden md:block">
            珠海保税区丽珠合成制药有限公司
          </span>
        </div>
      </div>

      {/* 移动端：当前模块名（点击下拉切换模块） */}
      <Dropdown
        trigger={["click"]}
        placement="bottomLeft"
        menu={{
          items: moduleMenus.map((mod) => ({
            key: mod.key,
            label: <Link href={mod.path}>{mod.label}</Link>,
            icon: <ModuleIcon name={mod.icon} className="w-4 h-4" />,
          })),
          selectedKeys: [activeModule],
        }}
      >
        <button className="md:hidden flex items-center gap-1 ml-2 mr-auto text-[15px] font-semibold text-[var(--color-ink)]">
          {moduleMenus.find((m) => m.key === activeModule)?.label || ""}
          <span className="text-[10px] text-[var(--color-steel)]">▾</span>
        </button>
      </Dropdown>

      {/* Module Tabs（仅桌面显示；移动端模块切换走导航抽屉） */}
      <nav className="hidden md:flex items-center gap-0.5 flex-1 overflow-x-auto scrollbar-hide h-full ml-8">
        {moduleMenus.map((mod) => {
          const isActive = activeModule === mod.key
          return (
            <Link
              key={mod.key}
              href={mod.path}
              className={`
                flex items-center gap-1.5 px-3 h-full text-[14px] font-medium transition-colors whitespace-nowrap relative
                ${isActive
                  ? "text-[var(--color-ink)]"
                  : "text-[var(--color-steel)] hover:text-[var(--color-charcoal)]"
                }
              `}
            >
              <ModuleIcon name={mod.icon} className="w-4 h-4" />
              {mod.label}
              {isActive && (
                <span className="absolute bottom-0 left-3 right-3 h-[2px] bg-[var(--color-primary)] rounded-full" />
              )}
            </Link>
          )
        })}
      </nav>

      {/* Right Section */}
      <div className="flex items-center gap-1 ml-4 shrink-0">
        <button
          onClick={toggleSidebar}
          className="w-8 h-8 items-center justify-center rounded-[var(--rounded-sm)] text-[var(--color-steel)] hover:text-[var(--color-charcoal)] hover:bg-[var(--color-surface)] transition-colors hidden md:flex"
          title={collapsed ? "展开侧边栏" : "收起侧边栏"}
        >
          {collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
        </button>
        <button className="w-8 h-8 flex items-center justify-center rounded-[var(--rounded-sm)] text-[var(--color-steel)] hover:text-[var(--color-charcoal)] hover:bg-[var(--color-surface)] transition-colors">
          <SearchIcon className="w-[18px] h-[18px]" />
        </button>
        <button className="w-8 h-8 flex items-center justify-center rounded-[var(--rounded-sm)] text-[var(--color-steel)] hover:text-[var(--color-charcoal)] hover:bg-[var(--color-surface)] transition-colors relative">
          <BellIcon className="w-[18px] h-[18px]" />
          <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[var(--color-error)] rounded-full" />
        </button>
        <Dropdown
          menu={{
            items: [
              {
                key: 'logout',
                label: '退出登录',
                icon: <LogoutOutlined />,
                danger: true,
              },
            ],
            onClick: (info) => {
              if (info.key === 'logout') handleLogout()
            },
          }}
          placement="bottomRight"
        >
          <button
            className="ml-2 flex items-center gap-2 h-8 px-2 rounded-[var(--rounded-md)] hover:bg-[var(--color-surface)] transition-colors disabled:opacity-50"
            disabled={loggingOut}
          >
            {avatarSrc ? (
              <Avatar src={avatarSrc} size={28} />
            ) : (
              <Avatar size={28} icon={<UserOutlined />} />
            )}
            <span className="text-[13px] text-[var(--color-ink)] hidden md:inline">
              {displayName}
            </span>
          </button>
        </Dropdown>
      </div>
    </header>
  )
}
