import { getCurrentUser } from '@/actions/auth'
import { LoginLogsClient, NoAccessResult, SettingsPageHeader } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function SettingsLoginLogsPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可查看登录记录。" />
  }

  if (!(await hasPermission(PERM.auditRead))) {
    return (
      <NoAccessResult subTitle="查看登录记录需要「操作记录查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6">
      <SettingsPageHeader
        title="登录记录"
        description="查看用户登录历史，包括成功与失败的登录尝试、来源 IP 与失败原因。"
      />
      <LoginLogsClient />
    </div>
  )
}
