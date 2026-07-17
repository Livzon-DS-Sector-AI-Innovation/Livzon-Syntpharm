import { fetchCpvProductServer, fetchCpvParametersServer } from '@/actions/quality-cpv'
import { CqaBatchDataClient } from '@/components/quality/CqaBatchDataClient'
import { notFound } from 'next/navigation'

export const dynamic = 'force-dynamic'

export default async function CqaBatchDataPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params

  let product, parameters
  try {
    ;[product, parameters] = await Promise.all([
      fetchCpvProductServer(productId),
      fetchCpvParametersServer(productId, 'CQA'),
    ])
  } catch {
    notFound()
  }

  return (
    <CqaBatchDataClient
      productId={productId}
      initialProduct={product!}
      initialParameters={parameters!}
    />
  )
}
