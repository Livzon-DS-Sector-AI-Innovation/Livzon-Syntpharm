import { fetchEmployees } from '@/actions/hr'
import { RosterClient } from '@/components/hr'

export const dynamic = 'force-dynamic'

export default async function RosterPage() {
  const res = await fetchEmployees({ page: 1, page_size: 20 })

  return (
    <RosterClient
      initialEmployees={res.data}
      initialTotal={res.meta?.total || 0}
    />
  )
}
