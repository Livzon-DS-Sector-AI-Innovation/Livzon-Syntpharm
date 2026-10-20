import { getCurrentUser } from '@/actions/auth'
import { NoAccessResult, PermissionAdminClient } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasAnyPermission } from '@/lib/permissions/server'

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

  // 角色管理 / 授权管理 / 权限目录三个 Tab 各自有权限：只要有一个就放行，
  // 具体 Tab 可见性由 PermissionAdminClient 按权限过滤。
  if (!(await hasAnyPermission([PERM.roleRead, PERM.grantRead, PERM.grantManage]))) {
    return (
      <NoAccessResult subTitle="访问权限管理需要「角色查看」或「授权管理」权限，请联系管理员为你的账号分配。" />
    )
  }

  // 支持 /settings/permission?tab=grants 直达「授权管理」（用户管理页会带这个参数）
  const { tab } = await searchParams
  return <PermissionAdminClient initialTab={tab} />
}
