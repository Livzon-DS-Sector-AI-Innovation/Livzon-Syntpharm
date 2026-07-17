export const dynamic = 'force-dynamic'

import { fetchTrainingSessionsAction } from '@/actions/hr'
import TrainingSessionListClient from '@/components/hr/TrainingSessionListClient'

export default async function TrainingRecordsPage() {
  const res = await fetchTrainingSessionsAction({ page: 1, page_size: 20 })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-2">
          培训列表
        </h1>
        <p className="text-[14px] text-[var(--color-steel)]">
          记录和管理历次培训活动
        </p>
      </div>

      <TrainingSessionListClient
        initialData={res.data || []}
        initialMeta={res.meta}
      />
    </div>
  )
}
