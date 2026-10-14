import { getCurrentUser } from '@/actions/auth'
import { AuditLogsClient, NoAccessResult } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function SettingsAuditPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可查看操作审计。" />
  }

  if (!(await hasPermission(PERM.auditRead))) {
    return (
      <NoAccessResult subTitle="查看操作审计需要「审计日志查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return (
    <div className="mx-auto max-w-[1320px] px-6 py-6">
      <div className="mb-5">
        <h1 className="m-0 text-[24px] font-semibold text-[var(--color-charcoal)]">
          操作审计
        </h1>
        <p className="m-0 mt-1 text-[13px] text-[var(--color-steel)]">
          记录账号、角色与授权的关键变更（谁在何时改了什么，改前 / 改后值），用于合规追溯与定期审阅。
        </p>
      </div>
      <AuditLogsClient />
    </div>
  )
}
