import { fetchEmployeeDepartmentsAction, fetchEmployeeProfilesAction, fetchOrgSyncStatus } from '@/actions/hr'
import { EmployeeDirectoryClient } from '@/components/hr'
import { unavailableOrgSyncStatus } from '@/lib/hr/orgSyncStatus'

export const dynamic = 'force-dynamic'

export default async function EmployeeProfilePage() {
  const [treeResult, peopleResult, statusResult] = await Promise.allSettled([
    fetchEmployeeDepartmentsAction(),
    fetchEmployeeProfilesAction({ status: '1', page: 1, page_size: 20 }),
    fetchOrgSyncStatus(),
  ])

  const tree = treeResult.status === 'fulfilled' ? treeResult.value.data.items ?? [] : []
  const people = peopleResult.status === 'fulfilled' ? peopleResult.value.data : undefined

  return (
    <EmployeeDirectoryClient
      initialTree={tree}
      initialPeople={people?.items ?? []}
      initialTotal={peopleResult.status === 'fulfilled' ? Number(peopleResult.value.meta?.total ?? 0) : 0}
      initialLastSyncedAt={people?.last_synced_at ?? null}
      initialStatus={statusResult.status === 'fulfilled' ? statusResult.value.data : unavailableOrgSyncStatus()}
    />
  )
}
