import { unwrapResponse } from '@/lib/api/server/base'
import { fetchOrgDepartments, fetchOrgSyncStatus } from '@/actions/hr'
import { DepartmentOrgClient } from '@/components/hr'
import { unavailableOrgSyncStatus } from '@/lib/hr/orgSyncStatus'

export const dynamic = 'force-dynamic'

export default async function DepartmentsPage() {
  const [treeResult, statusResult] = await Promise.allSettled([fetchOrgDepartments(), fetchOrgSyncStatus()])

  const tree = treeResult.status === 'fulfilled' ? unwrapResponse(treeResult.value).items ?? [] : []
  const status =
    statusResult.status === 'fulfilled' ? unwrapResponse(statusResult.value) : unavailableOrgSyncStatus()

  return <DepartmentOrgClient initialTree={tree} initialStatus={status} />
}
