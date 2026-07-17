import PurchaseOrderClientWrapper from '@/components/procurement/PurchaseOrderClientWrapper'
import { fetchPurchaseOrders } from '@/lib/api/server/procurement'

export const dynamic = 'force-dynamic'

const DEFAULT_PAGE_SIZE = 20

export default async function PurchaseOrderPage() {
  const now = new Date()
  const initialYear = now.getFullYear()
  const initialMonth = now.getMonth() + 1

  const response = await fetchPurchaseOrders({
    year: initialYear,
    month: initialMonth,
    page: 1,
    page_size: DEFAULT_PAGE_SIZE,
  }).catch(() => ({
    code: 200,
    message: 'success',
    data: [],
    meta: {
      page: 1,
      page_size: DEFAULT_PAGE_SIZE,
      total: 0,
    },
  }))

  return (
    <PurchaseOrderClientWrapper
      initialLines={response.data}
      initialTotal={Number(response.meta?.total ?? response.data.length)}
      initialYear={initialYear}
      initialMonth={initialMonth}
    />
  )
}
