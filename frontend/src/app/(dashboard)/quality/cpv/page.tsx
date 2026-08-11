import { fetchCpvProductsServer } from '@/actions/quality-cpv'
import { CpvProductListClient } from '@/components/quality/CpvProductListClient'
import type { CpvProductWithStats } from '@/types/quality-cpv'

export const dynamic = 'force-dynamic'

export default async function CpvProductListPage() {
  const result = await fetchCpvProductsServer({ page: 1, page_size: 50 })

  return (
    <>
      <h1 className="text-2xl font-semibold text-gray-800 mb-4">CPV产品管理</h1>
      <CpvProductListClient initialProducts={(result.items ?? []) as CpvProductWithStats[]} />
    </>
  )
}
