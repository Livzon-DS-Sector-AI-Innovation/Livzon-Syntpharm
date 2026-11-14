import { unwrapResponse } from '@/lib/api/server/base'
import { fetchOnboardingRecords } from '@/actions/hr'
import { OnboardingClient } from '@/components/hr'

export const dynamic = 'force-dynamic'

export default async function OnboardingPage() {
  const res = await fetchOnboardingRecords({ page: 1, page_size: 20 })

  return (
    <OnboardingClient
      initialRecords={unwrapResponse(res)}
      initialTotal={Number(res.meta?.total ?? 0)}
    />
  )
}
