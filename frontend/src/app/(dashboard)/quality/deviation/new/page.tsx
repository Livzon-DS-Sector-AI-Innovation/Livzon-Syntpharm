import type { Metadata } from 'next'
import { getCurrentUser } from '@/actions/auth'
import { DeviationCreateForm } from '@/components/quality/deviation'
import { getDeviationDepartmentContactOptions } from '@/lib/api/server/quality'
import type { DeviationLedgerOption } from '@/types/quality'

// 候选数据随组织与人员变化，禁用静态预渲染
export const dynamic = 'force-dynamic'

export const metadata: Metadata = { title: '新建偏差' }

export default async function DeviationCreatePage() {
  // 部门候选取不到时表单仍可打开：下拉为空，用户联系管理员补数据；
  // 人员候选改由 RemoteUserSelect 展开时远端加载，不再预取全量用户
  const [departmentResult, user] = await Promise.all([
    getDeviationDepartmentContactOptions().catch((error) => {
      console.error('偏差部门候选加载失败', error)
      return [] as DeviationLedgerOption[]
    }),
    getCurrentUser().catch((error) => {
      console.error('当前登录人加载失败', error)
      return null
    }),
  ])

  return (
    <DeviationCreateForm
      departmentOptions={departmentResult}
      currentUserId={user?.id ?? ''}
      currentUserName={user?.name ?? ''}
    />
  )
}