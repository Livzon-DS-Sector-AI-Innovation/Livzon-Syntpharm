import type { ValidationAuditTaskListItem } from '@/types/validation-audit'
import { fetchTasksServer } from '@/actions/validation-audit'
import { ValidationAuditListClient } from '@/components/registration'

export const dynamic = 'force-dynamic'

export default async function ValidationAuditPage() {
  const res = await fetchTasksServer({ page: 1, page_size: 20 })
  const data = res?.data as Record<string, unknown> | undefined
  const items = ((data as any)?.items as ValidationAuditTaskListItem[]) || ((res?.data as any) as ValidationAuditTaskListItem[]) || []
  const meta = res?.meta as Record<string, unknown> | undefined
  const total = ((meta as any)?.total as number) || ((data as any)?.total as number) || 0

  return (
    <ValidationAuditListClient
      initialTasks={items as ValidationAuditTaskListItem[]}
      initialTotal={total}
    />
  )
}
