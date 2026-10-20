'use client'

import { useEffect, useState } from "react"
import { App, Drawer } from "antd"
import { useQueryClient } from "@tanstack/react-query"
import { TopNav } from "./TopNav"
import { Sidebar } from "./Sidebar"
import type { PermissionView } from "@/lib/permissions/modules"
import type { User } from "@/types/user"

interface AppShellProps {
  children: React.ReactNode
  /** 服务端解析的权限视图（可见模块 / 权限码），下发给顶部导航与侧边栏 */
  permissionView: PermissionView
  /** 当前登录用户 id：切换账号后与客户端查询缓存比对，不一致就清空 */
  userId: string
  /** 当前登录用户展示信息（服务端下发，避免首屏「未登录」闪动） */
  userName: string
  avatarUrl?: string | null
}

export function AppShell({
  children,
  permissionView,
  userId,
  userName,
  avatarUrl,
}: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const queryClient = useQueryClient()

  // 切换账号（换 cookie 后服务端渲染出新 user.id）时，客户端 React Query 里可能
  // 还留着上一个账号的 current-user / my-permissions。清空缓存，避免新账号沿用
  // 旧权限渲染按钮与菜单，必须手动刷新才正常。
  useEffect(() => {
    const cached = queryClient.getQueryData<User | null>(['current-user'])
    if (cached?.id !== userId) {
      queryClient.clear()
    }
  }, [userId, queryClient])

  return (
    <App>
      <div className="h-screen flex flex-col overflow-hidden">
        <TopNav
          permissionView={permissionView}
          userName={userName}
          avatarUrl={avatarUrl}
          onMenuClick={() => setSidebarOpen(true)}
        />
        <div className="flex flex-1 overflow-hidden">
          {/* 桌面侧栏：md(≥768px) 显示；移动端由下方 Drawer 承载，用 CSS 决定显示避免首屏闪动 */}
          <div className="hidden md:flex shrink-0 overflow-hidden">
            <Sidebar permissionView={permissionView} />
          </div>
          <Drawer
            placement="left"
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            styles={{ body: { padding: 0 }, wrapper: { width: 256 } }}
          >
            <Sidebar permissionView={permissionView} forceExpanded onNavigate={() => setSidebarOpen(false)} />
          </Drawer>
          <main className="flex-1 overflow-y-auto bg-[var(--color-surface)] p-3 md:p-6">
            {children}
          </main>
        </div>
      </div>
    </App>
  )
}
