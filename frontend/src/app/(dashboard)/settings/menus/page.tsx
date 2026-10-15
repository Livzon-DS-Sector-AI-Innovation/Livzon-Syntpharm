import { getCurrentUser } from '@/actions/auth'
import { MenuManagerClient, NoAccessResult, SettingsPageHeader } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function SettingsMenusPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可管理菜单。" />
  }

  if (!(await hasPermission(PERM.opsRead))) {
    return (
      <NoAccessResult subTitle="菜单管理需要「系统运维查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6">
      <SettingsPageHeader
        title="菜单管理"
        description="配置顶部导航与左侧菜单的显隐、排列权重与可见权限，也可新增自定义菜单项。未配置的菜单项按代码默认渲染。"
      />
      <MenuManagerClient />
    </div>
  )
}
