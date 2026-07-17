import { ContractSummaryClient } from '@/components/procurement'
import { fetchContractRecords } from '@/lib/api/server/procurement'
import type { ContractRecordResponse } from '@/types/procurement'

export const dynamic = 'force-dynamic'

const DEFAULT_PAGE_SIZE = 12

export default async function ContractSummaryPage() {
  let records: ContractRecordResponse[] = []
  let total = 0
  let initialLoadFailed = false

  try {
    const response = await fetchContractRecords({
      page: 1,
      page_size: DEFAULT_PAGE_SIZE,
    })
    records = response.data ?? []
    total = Number(response.meta?.total ?? records.length)
  } catch {
    initialLoadFailed = true
  }

  return (
    <ContractSummaryClient
      initialRecords={records}
      initialTotal={Number.isFinite(total) ? total : records.length}
      initialLoadFailed={initialLoadFailed}
    />
  )
}
