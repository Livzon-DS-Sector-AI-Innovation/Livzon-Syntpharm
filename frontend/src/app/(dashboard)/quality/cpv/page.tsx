import { fetchCpvProductsServer } from '@/actions/quality-cpv'
import { CpvProductListClient } from '@/components/quality/CpvProductListClient'

export const dynamic = 'force-dynamic'

export default async function CpvProductListPage() {
  const result = await fetchCpvProductsServer({ page: 1, page_size: 50 })

  return <CpvProductListClient initialProducts={result.items} />
}
