import { fetchCpvProductServer, fetchCpvParametersServer } from '@/actions/quality-cpv'
import { CpvProductDetailClient } from '@/components/quality/CpvProductDetailClient'
import { notFound } from 'next/navigation'

export const dynamic = 'force-dynamic'

export default async function CpvProductDetailPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params

  let product, cppParams, cqaParams
  try {
    ;[product, cppParams, cqaParams] = await Promise.all([
      fetchCpvProductServer(productId),
      fetchCpvParametersServer(productId, 'CPP'),
      fetchCpvParametersServer(productId, 'CQA'),
    ])
  } catch {
    notFound()
  }

  return (
    <CpvProductDetailClient
      productId={productId}
      initialProduct={product!}
      initialCppParams={cppParams!}
      initialCqaParams={cqaParams!}
    />
  )
}
