import { unwrapResponse } from '@/lib/api/server/base'
import { fetchCandidateById } from '@/actions/hr'
import { CandidateDetailClient } from '@/components/hr'

export const dynamic = 'force-dynamic'

interface CandidateDetailPageProps {
  params: Promise<{ id: string }>
}

export default async function CandidateDetailPage({ params }: CandidateDetailPageProps) {
  const { id } = await params
  const res = await fetchCandidateById(id)

  return (
    <div className="space-y-4">
      <h1 className="m-0 text-[22px] font-semibold text-[var(--color-charcoal)]">简历详情</h1>
      <CandidateDetailClient candidate={unwrapResponse(res)} />
    </div>
  )
}
