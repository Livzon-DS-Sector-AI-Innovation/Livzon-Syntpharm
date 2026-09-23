import type { ValidationAuditTaskListItem } from '@/types/validation-audit'
import { fetchTasksServer } from '@/actions/validation-audit'
import { ValidationAuditListClient } from '@/components/registration'

export const dynamic = 'force-dynamic'

export default async function ValidationAuditPage() {
  const res = await fetchTasksServer({ page: 1, page_size: 20 })
  const data = res?.data as Record<string, unknown> | undefined
  const items = (data?.items as ValidationAuditTaskListItem[] | undefined) || (res?.data as unknown as ValidationAuditTaskListItem[]) || []
  const meta = res?.meta as Record<string, unknown> | undefined
  const total = (meta?.total as number | undefined) || (data?.total as number | undefined) || 0

  return (
    <ValidationAuditListClient
      initialTasks={items as ValidationAuditTaskListItem[]}
      initialTotal={total}
    />
  )
}
