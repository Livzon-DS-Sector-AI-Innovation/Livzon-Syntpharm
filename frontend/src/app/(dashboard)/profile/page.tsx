import { redirect } from 'next/navigation'
import { getCurrentUser } from '@/actions/auth'
import { ProfileClient } from '@/components/profile'
import { getPermissionsSnapshot } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

/** 个人信息（头像下拉 → 个人信息）。 */
export default async function ProfilePage() {
  const user = await getCurrentUser()
  if (!user) redirect('/login')

  const snapshot = await getPermissionsSnapshot()

  return (
    <ProfileClient
      user={{
        name: user.name,
        username: user.username,
        employeeNo: user.employee_no,
        department: user.department,
        position: user.position,
        email: user.email,
        mobile: user.mobile,
        authSource: user.auth_source,
        avatarUrl: user.avatar_url,
        status: user.status,
        mustChangePassword: Boolean(user.must_change_password),
      }}
      isSuperuser={snapshot?.isSuperuser ?? false}
      permissionCount={snapshot?.permissions.length ?? 0}
    />
  )
}
