import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/actions/auth'
import { NoAccessResult } from '@/components/settings'
import { resolveLandingPath } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

/**
 * 根路径 = 登录后的落地页。
 *
 * 跳转到「第一个可见模块」的首页；未接入权限控制的模块恒可见，
 * 因此只要还有未接入的模块（当前除系统管理外的 12 个），落地页行为与以前一致。
 */
export default async function RootPage() {
  const user = await getCurrentUser()

  if (!user) {
    redirect('/login')
  }

  const landingPath = await resolveLandingPath()

  if (landingPath) {
    redirect(landingPath)
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-[var(--color-surface)] p-6">
      <NoAccessResult
        title="暂无可访问的模块"
        subTitle="当前账号还没有分配任何模块权限，请联系管理员为你的账号授权。"
      />
    </div>
  )
}
