import { redirect } from 'next/navigation'
import { AntdProvider } from '@/components/AntdProvider'
import { ChangePasswordClient } from '@/components/settings'
import { getCurrentUser } from '@/actions/auth'

// 依赖运行时用户信息（读 cookie + 调后端 /identity/me），不能静态预渲染
export const dynamic = 'force-dynamic'

/**
 * 自助改密页（位于 (dashboard) 之外：否则会被「强制改密」重定向打成死循环）。
 *
 * 访问条件：已登录。已改过密的用户可以主动进来改密；
 * 被标记 `must_change_password` 的用户由 (dashboard)/layout.tsx 强制送到这里。
 */
export default async function ChangePasswordPage() {
  const user = await getCurrentUser()

  if (!user) {
    redirect('/login')
  }

  return (
    <AntdProvider>
      <ChangePasswordClient userName={user.name} forced={!!user.must_change_password} />
    </AntdProvider>
  )
}
