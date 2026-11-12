import { fetchOrgDepartments, fetchOrgSyncStatus } from '@/actions/hr'
import { DepartmentOrgClient } from '@/components/hr'

export const dynamic = 'force-dynamic'

export default async function DepartmentsPage() {
  const [treeResult, statusResult] = await Promise.allSettled([fetchOrgDepartments(), fetchOrgSyncStatus()])

  const tree = treeResult.status === 'fulfilled' ? treeResult.value.data.items ?? [] : []
  const status =
    statusResult.status === 'fulfilled'
      ? statusResult.value.data
      : {
          status: 'failed',
          last_synced_at: null,
          department_count: 0,
          people_count: 0,
          error_message: '同步状态暂时不可用',
        }

  return <DepartmentOrgClient initialTree={tree} initialStatus={status} />
}
