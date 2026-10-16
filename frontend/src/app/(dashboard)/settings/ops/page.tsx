import { getCurrentUser } from '@/actions/auth'
import { NoAccessResult } from '@/components/settings'
import SystemOpsClient from '@/components/settings/SystemOpsClient'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function SystemOpsPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可访问系统运维。" />
  }

  if (!(await hasPermission(PERM.opsRead))) {
    return (
      <NoAccessResult subTitle="访问系统运维需要「系统运维查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return <SystemOpsClient />
}
