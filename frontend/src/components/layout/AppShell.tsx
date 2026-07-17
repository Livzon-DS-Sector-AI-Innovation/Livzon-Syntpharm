'use client'
"use client"

import { useState, useEffect } from "react"
import { App, Drawer } from "antd"
import { TopNav } from "./TopNav"
import { Sidebar } from "./Sidebar"
import { MenuOutlined } from "@ant-design/icons"

interface AppShellProps {
  children: React.ReactNode
}

export function AppShell({ children }: AppShellProps) {
  const [isMobile, setIsMobile] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(false)

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])

  const sidebarContent = <Sidebar onNavigate={() => setSidebarOpen(false)} />

  return (
    <App>
      <div className="h-screen flex flex-col overflow-hidden">
        <TopNav
          onMenuClick={() => setSidebarOpen(true)}
          showMenuButton={isMobile}
        />
        <div className="flex flex-1 overflow-hidden">
          {isMobile ? (
            <Drawer
              placement="left"
              open={sidebarOpen}
              onClose={() => setSidebarOpen(false)}
              styles={{ body: { padding: 0 } }}
              width={256}
            >
              {sidebarContent}
            </Drawer>
          ) : (
            sidebarContent
          )}
          <main className={`flex-1 overflow-y-auto bg-[var(--color-surface)] ${isMobile ? 'p-3' : 'p-6'}`}>
            {children}
          </main>
        </div>
        </div>
    </App>
  )
}
