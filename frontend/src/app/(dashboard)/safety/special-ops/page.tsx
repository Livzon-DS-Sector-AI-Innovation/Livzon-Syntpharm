import SpecialOpsManagementWrapper from '@/components/safety/SpecialOpsManagementWrapper'
import { getSpecialOperationLedgerStats } from '@/actions/safety'
import type { SpecialOperationLedgerStats } from '@/types/safety'

export const dynamic = 'force-dynamic'

export default async function SpecialOpsPage() {
  let initialStats: SpecialOperationLedgerStats[] = []
  try {
    const res = await getSpecialOperationLedgerStats()
    if (res.code === 200) initialStats = res.data || []
  } catch { /* client will refetch */ }

  return (
    <>
      <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-4">特殊作业</h1>
      <SpecialOpsManagementWrapper initialStats={initialStats} />
    </>
  )
}
