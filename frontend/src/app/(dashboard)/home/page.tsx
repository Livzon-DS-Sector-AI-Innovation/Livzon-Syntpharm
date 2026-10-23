import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/actions/auth'
import { HomeWorkspace, type HomeModuleEntry } from '@/components/home'
import { resolveMenus } from '@/lib/menu/resolve'
import { getPermissionView } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

/**
 * 首页（工作台）= 登录后的默认落地页。
 *
 * 快捷入口只渲染当前账号真正能进的模块。`settings` 现在的根路径是概览页，
 * 对模块内所有账号开放，因此直接落到模块根路径即可。
 */
export default async function HomePage() {
  const user = await getCurrentUser()
  if (!user) redirect('/login')

  const view = await getPermissionView()
  const granted = new Set(view.granted)
  const modules = resolveMenus(view.menuConfig, granted, view.isSuperuser)

  const entries: HomeModuleEntry[] = modules.map((mod) => ({
    key: mod.key,
    label: mod.label,
    icon: mod.icon,
    path: mod.path,
  }))

  const today = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    weekday: 'long',
  }).format(new Date())

  return (
    <HomeWorkspace
      userName={user.name}
      department={user.department}
      position={user.position}
      today={today}
      modules={entries}
    />
  )
}
