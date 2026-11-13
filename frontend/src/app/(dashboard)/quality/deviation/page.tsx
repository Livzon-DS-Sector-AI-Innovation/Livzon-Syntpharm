import type { Metadata } from 'next'
import { DeviationDashboard } from '@/components/quality/deviation'
import { fetchDeviationLedgerStatistics } from '@/lib/api/server/quality'
import type { DeviationLedgerStatistics } from '@/types/quality'

// 统计随时在变，禁用静态预渲染
export const dynamic = 'force-dynamic'

export const metadata: Metadata = { title: '偏差管理' }

export default async function DeviationManagementPage() {
  // 统计失败不阻塞页面：降级为空态 + 顶部告警条，用户仍可进台账
  let statistics: DeviationLedgerStatistics | null = null
  try {
    statistics = await fetchDeviationLedgerStatistics()
  } catch (error) {
    console.error('偏差看盘统计加载失败', error)
  }

  return <DeviationDashboard initialStatistics={statistics} />
}