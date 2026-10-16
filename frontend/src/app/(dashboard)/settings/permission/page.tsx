import { getCurrentUser } from '@/actions/auth'
import { NoAccessResult, PermissionAdminClient } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function PermissionPage({
  searchParams,
}: {
  searchParams: Promise<{ tab?: string }>
}) {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可访问权限管理。" />
  }

  if (!(await hasPermission(PERM.roleRead))) {
    return (
      <NoAccessResult subTitle="访问权限管理需要「角色查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  // 支持 /settings/permission?tab=grants 直达「授权管理」（用户管理页会带这个参数）
  const { tab } = await searchParams
  return <PermissionAdminClient initialTab={tab} />
}
