import { notFound } from 'next/navigation'
import { QcReportClient } from '@/components/quality/qc-report'
import {
  fetchQcBatches,
  fetchQcItems,
  fetchQcProductOrNull,
  fetchQcStats,
} from '@/lib/api/server/qc-report'
import type { QcBatchPageData, QcItem, QcStats } from '@/types/qc-report'

export const dynamic = 'force-dynamic'

export default async function QcReportPage({ params }: { params: Promise<{ productId: string }> }) {
  const { productId } = await params

  // 品种被删掉后再进来属于正常情况（书签、历史记录），直接走 404
  const product = await fetchQcProductOrNull(productId)
  if (!product) notFound()

  let items: QcItem[]
  let batches: QcBatchPageData
  let stats: QcStats

  try {
    ;[items, batches, stats] = await Promise.all([
      fetchQcItems(productId),
      fetchQcBatches({ productId, page: 1, page_size: 50 }),
      fetchQcStats(productId),
    ])
  } catch (error) {
    console.error('检验数据报表加载失败', error)
    return (
      <div className="p-6">
        <div className="rounded-xl border border-[#e5e3df] bg-white px-6 py-14 text-center">
          <p className="text-[16px] font-medium text-[#1a1a1a]">检验数据加载失败</p>
          <p className="mt-1 text-[13px] text-[#5d5b54]">品种存在，但明细数据暂时取不到，请稍后刷新重试</p>
        </div>
      </div>
    )
  }

  return (
    <QcReportClient
      productId={productId}
      productName={product.name}
      abbr={product.abbr}
      qualityStandard={product.quality_standard}
      initialItems={items}
      initialBatches={batches}
      initialStats={stats}
    />
  )
}
