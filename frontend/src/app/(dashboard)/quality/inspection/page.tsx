import { QcProductListClient } from '@/components/quality/qc-report'
import { fetchQcAttentionBatches, fetchQcProducts } from '@/lib/api/server/qc-report'
import type { QcAttentionBatch, QcProductListItem } from '@/types/qc-report'

export const dynamic = 'force-dynamic'

export default async function QcInspectionPage() {
  let products: QcProductListItem[] = []
  let attention: QcAttentionBatch[] = []
  let loadFailed = false

  // 读操作直接走 server 取数并兜底：任一接口失败只降级展示，不让整页 500
  try {
    products = await fetchQcProducts()
  } catch (error) {
    console.error('质量检验品种列表加载失败', error)
    loadFailed = true
  }

  try {
    attention = await fetchQcAttentionBatches(20)
  } catch (error) {
    console.error('需关注批号加载失败', error)
  }

  return (
    <QcProductListClient
      initialProducts={products}
      initialAttention={attention}
      loadFailed={loadFailed}
    />
  )
}
