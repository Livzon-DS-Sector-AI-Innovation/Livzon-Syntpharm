import { getCurrentUser } from '@/actions/auth'
import SettingsAdminClient from '@/components/settings/SettingsAdminClient'
import { NoAccessResult } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

/** 平台配置：LLM 模型、飞书设置、Livzon Skill（原 /settings 的内容）。 */
export default async function SettingsPlatformPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可访问平台配置。" />
  }

  if (!(await hasPermission(PERM.configRead))) {
    return (
      <NoAccessResult subTitle="访问平台配置需要「平台配置查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return <SettingsAdminClient />
}
