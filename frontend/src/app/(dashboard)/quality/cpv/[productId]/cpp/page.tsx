import { fetchCpvProductServer, fetchCpvParametersServer } from '@/actions/quality-cpv'
import { CppBatchDataClient } from '@/components/quality/CppBatchDataClient'
import { notFound } from 'next/navigation'

export const dynamic = 'force-dynamic'

export default async function CppBatchDataPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params

  let product, parameters
  try {
    ;[product, parameters] = await Promise.all([
      fetchCpvProductServer(productId),
      fetchCpvParametersServer(productId, 'CPP'),
    ])
  } catch {
    notFound()
  }

  return (
    <CppBatchDataClient
      productId={productId}
      initialProduct={product!}
      initialParameters={parameters!}
    />
  )
}
