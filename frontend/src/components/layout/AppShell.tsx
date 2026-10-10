'use client'

import { useState } from "react"
import { App, Drawer } from "antd"
import { TopNav } from "./TopNav"
import { Sidebar } from "./Sidebar"

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <App>
      <div className="h-screen flex flex-col overflow-hidden">
        <TopNav onMenuClick={() => setSidebarOpen(true)} />
        <div className="flex flex-1 overflow-hidden">
          {/* 桌面侧栏：md(≥768px) 显示；移动端由下方 Drawer 承载，用 CSS 决定显示避免首屏闪动 */}
          <div className="hidden md:flex shrink-0 overflow-hidden">
            <Sidebar />
          </div>
          <Drawer
            placement="left"
            open={sidebarOpen}
            onClose={() => setSidebarOpen(false)}
            styles={{ body: { padding: 0 }, wrapper: { width: 256 } }}
          >
            <Sidebar forceExpanded onNavigate={() => setSidebarOpen(false)} />
          </Drawer>
          <main className="flex-1 overflow-y-auto bg-[var(--color-surface)] p-3 md:p-6">
            {children}
          </main>
        </div>
      </div>
    </App>
  )
}
