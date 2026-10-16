import { getCurrentUser } from '@/actions/auth'
import SettingsAdminClient from '@/components/settings/SettingsAdminClient'
import { NoAccessResult } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function SettingsPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可访问系统设置。" />
  }

  // 本页只装平台配置类（LLM / 飞书 / Skill），权限口径 = 平台配置查看；
  // 用户管理、登录记录、权限管理、系统运维都是独立页面，各有自己的守卫。
  if (!(await hasPermission(PERM.configRead))) {
    return (
      <NoAccessResult subTitle="访问系统设置需要「平台配置查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return <SettingsAdminClient />
}
