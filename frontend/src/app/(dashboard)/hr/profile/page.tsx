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

interface EmployeeProfilePageProps {
  /** 支持 ?open_id=<飞书 open_id> 定位到具体员工（用户管理「查看档案」跳转入口） */
  searchParams: Promise<{ open_id?: string | string[] }>
}

export default async function EmployeeProfilePage({ searchParams }: EmployeeProfilePageProps) {
  const params = await searchParams
  const rawOpenId = params.open_id
  const initialOpenId = (Array.isArray(rawOpenId) ? rawOpenId[0] : rawOpenId)?.trim() || null

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
      initialOpenId={initialOpenId}
    />
  )
}
