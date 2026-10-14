import { getCurrentUser } from '@/actions/auth'
import { NoAccessResult, UserManagementClient } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function SettingsUsersPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可访问用户管理。" />
  }

  if (!(await hasPermission(PERM.userRead))) {
    return (
      <NoAccessResult subTitle="访问用户管理需要「用户查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return (
    <div className="mx-auto max-w-[1320px] md:px-6 md:py-6">
      <div className="mb-5">
        <h1 className="m-0 text-[24px] font-semibold text-[var(--color-charcoal)]">
          用户管理
        </h1>
        <p className="m-0 mt-1 text-[13px] text-[var(--color-steel)]">
          管理平台账号、角色授权与飞书绑定；登录历史见左侧「登录记录」。LLM 模型配置、飞书设置见「系统设置」。
        </p>
      </div>
      <UserManagementClient />
    </div>
  )
}
