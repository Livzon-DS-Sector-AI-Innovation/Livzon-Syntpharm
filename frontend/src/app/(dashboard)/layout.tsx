import { AppShell } from "@/components/layout/AppShell"
import { AntdProvider } from "@/components/AntdProvider"
import { getCurrentUser } from "@/actions/auth"
import { getPermissionView } from "@/lib/permissions/server"
import { redirect } from "next/navigation"
import '@/lib/dayjs-config'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const user = await getCurrentUser()

  if (!user) {
    redirect('/login')
  }

  // 密码被管理员重置过（或仍是初始密码）→ 先去改密，改完才放行其它页面。
  // 改密页在 (dashboard) 之外（app/change-password），所以这里 redirect 不会自环。
  if (user.must_change_password) {
    redirect('/change-password')
  }

  // 导航可见性在服务端算好再下发，避免客户端「先渲染全部 Tab、拿到权限后再消失」的闪烁。
  // 规则：未接入权限控制的模块恒可见（见 lib/permissions/modules.ts）。
  const permissionView = await getPermissionView()

  return (
    <AntdProvider>
      <AppShell permissionView={permissionView}>{children}</AppShell>
    </AntdProvider>
  )
}
