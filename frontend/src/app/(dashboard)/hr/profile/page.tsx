import { fetchEmployeeDepartmentsAction, fetchEmployeeProfilesAction, fetchOrgSyncStatus } from '@/actions/hr'
import { EmployeeDirectoryClient } from '@/components/hr'
import { unwrapResponse } from '@/lib/api/server/base'
import { unavailableOrgSyncStatus } from '@/lib/hr/orgSyncStatus'
import type { EmployeeProfileListData, OrgDepartmentTreeResponse } from '@/types/hr'

export const dynamic = 'force-dynamic'

function unwrapOrNull<T>(result: PromiseSettledResult<Parameters<typeof unwrapResponse>[0]>): T | null {
  if (result.status !== 'fulfilled') return null
  try {
    return unwrapResponse(result.value) as T
  } catch {
    return null
  }
}

export default async function EmployeeProfilePage() {
  const [treeResult, peopleResult, statusResult] = await Promise.allSettled([
    fetchEmployeeDepartmentsAction(),
    fetchEmployeeProfilesAction({ status: '1', page: 1, page_size: 20 }),
    fetchOrgSyncStatus(),
  ])

  const treeData = unwrapOrNull<OrgDepartmentTreeResponse['data']>(treeResult)
  const people = unwrapOrNull<EmployeeProfileListData>(peopleResult)
  const status = statusResult.status === 'fulfilled' ? statusResult.value : unavailableOrgSyncStatus()

  return (
    <EmployeeDirectoryClient
      initialTree={treeData?.items ?? []}
      initialPeople={people?.items ?? []}
      initialTotal={peopleResult.status === 'fulfilled' ? Number(peopleResult.value.meta?.total ?? 0) : 0}
      initialLastSyncedAt={people?.last_synced_at ?? null}
      initialStatus={status}
    />
  )
}
