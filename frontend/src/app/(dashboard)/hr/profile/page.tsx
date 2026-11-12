import { fetchEmployeeDepartmentsAction, fetchEmployeeProfilesAction } from '@/actions/hr'
import { EmployeeDirectoryClient } from '@/components/hr'

export const dynamic = 'force-dynamic'

export default async function EmployeeProfilePage() {
  const [treeResult, peopleResult] = await Promise.allSettled([
    fetchEmployeeDepartmentsAction(),
    fetchEmployeeProfilesAction({ page: 1, page_size: 20 }),
  ])

  const tree = treeResult.status === 'fulfilled' ? treeResult.value.data.items ?? [] : []
  const companyName = treeResult.status === 'fulfilled' ? treeResult.value.data.company_name ?? '' : ''
  const people = peopleResult.status === 'fulfilled' ? peopleResult.value.data : undefined

  return (
    <EmployeeDirectoryClient
      initialTree={tree}
      initialPeople={people?.items ?? []}
      initialTotal={peopleResult.status === 'fulfilled' ? Number(peopleResult.value.meta?.total ?? 0) : 0}
      initialLastSyncedAt={people?.last_synced_at ?? null}
      initialCompanyName={companyName}
    />
  )
}
