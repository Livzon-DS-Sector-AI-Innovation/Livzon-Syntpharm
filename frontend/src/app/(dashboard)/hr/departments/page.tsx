import { fetchOrgDepartments, fetchOrgSyncStatus } from '@/actions/hr'
import { DepartmentOrgClient } from '@/components/hr'
import { unavailableOrgSyncStatus } from '@/lib/hr/orgSyncStatus'

export const dynamic = 'force-dynamic'

export default async function DepartmentsPage() {
  const [treeResult, statusResult] = await Promise.allSettled([fetchOrgDepartments(), fetchOrgSyncStatus()])

  const tree = treeResult.status === 'fulfilled' ? treeResult.value.data.items ?? [] : []
  const status =
    statusResult.status === 'fulfilled' ? statusResult.value.data : unavailableOrgSyncStatus()

  return <DepartmentOrgClient initialTree={tree} initialStatus={status} />
}
