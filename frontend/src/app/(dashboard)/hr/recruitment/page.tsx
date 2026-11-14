import { unwrapResponse } from '@/lib/api/server/base'
import { fetchCandidates } from '@/actions/hr'
import { RecruitmentClient } from '@/components/hr'

export const dynamic = 'force-dynamic'

export default async function RecruitmentPage() {
  const res = await fetchCandidates({ page: 1, page_size: 20 })

  return (
    <RecruitmentClient
      initialCandidates={unwrapResponse(res)}
      initialTotal={res.meta?.total || 0}
    />
  )
}
