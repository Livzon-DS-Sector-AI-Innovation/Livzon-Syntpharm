import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/actions/auth'

export const dynamic = 'force-dynamic'

/**
 * 根路径 = 登录后的落地页，统一进入首页（工作台）。
 *
 * 首页本身对所有已登录账号开放；没有任何模块权限的账号会在工作台里看到
 * 「暂无可访问的模块」空态与「退出登录」入口。
 */
export default async function RootPage() {
  const user = await getCurrentUser()

  if (!user) {
    redirect('/login')
  }

  // 强制改密优先于首页：否则「无任何模块权限」的账号也可能拿不到改密入口
  if (user.must_change_password) {
    redirect('/change-password')
  }

  redirect('/home')
}
