import { getCurrentUser } from '@/actions/auth'
import { AuditLogsClient, NoAccessResult, SettingsPageHeader } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function SettingsAuditPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可查看操作记录。" />
  }

  if (!(await hasPermission(PERM.auditRead))) {
    return (
      <NoAccessResult subTitle="查看操作记录需要「操作记录查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6">
      <SettingsPageHeader
        title="操作记录"
        description="记录账号、角色与授权的关键变更（谁在何时改了什么，改前 / 改后值），用于追溯与定期审阅。"
      />
      <AuditLogsClient />
    </div>
  )
}
