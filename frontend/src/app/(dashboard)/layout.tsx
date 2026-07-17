import '@/lib/http-server'
import { AppShell } from "@/components/layout/AppShell"
import { AntdProvider } from "@/components/AntdProvider"
import { getCurrentUser } from "@/actions/auth"
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

  return (
    <AntdProvider>
      <AppShell>{children}</AppShell>
    </AntdProvider>
  )
}