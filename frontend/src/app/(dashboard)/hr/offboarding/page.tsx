import { unwrapResponse } from '@/lib/api/server/base'
import { fetchDepartureRecords } from '@/actions/hr'
import { DepartureClient } from '@/components/hr'

export const dynamic = 'force-dynamic'

export default async function OffboardingPage() {
  const res = await fetchDepartureRecords({ page: 1, page_size: 20 })

  return <DepartureClient initialRecords={unwrapResponse(res)} initialTotal={Number(res.meta?.total ?? 0)} />
}
