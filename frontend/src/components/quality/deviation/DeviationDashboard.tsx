'use client'

import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { useTransition } from 'react'
import { Alert, Breadcrumb, Button } from 'antd'
import { PlusOutlined, ReloadOutlined } from '@ant-design/icons'
import type { DeviationLedgerStatistics } from '@/types/quality'
import { DeviationDistributionCharts } from './DeviationDistributionCharts'
import { DeviationStatCards } from './DeviationStatCards'
import { DEVIATION_OVERDUE_HINT } from './constants'

interface DeviationDashboardProps {
  /** 首屏统计由 Server Component 取好；为 null 表示后端取数失败（降级为空态） */
  initialStatistics: DeviationLedgerStatistics | null
}

export function DeviationDashboard({ initialStatistics }: DeviationDashboardProps) {
  const router = useRouter()
  const [isRefreshing, startRefresh] = useTransition()

  const handleRefresh = () => {
    startRefresh(() => {
      router.refresh()
    })
  }

  return (
    <div className="flex flex-col gap-5">
      <header className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Breadcrumb
            className="mb-1"
            items={[{ title: <Link href="/quality">质量管理</Link> }, { title: '偏差管理' }]}
          />
          <h1 className="text-[22px] font-semibold text-[var(--color-ink)]">偏差管理</h1>
          <p className="mt-1 text-[13px] text-[var(--color-slate)]">
            偏差从发现到关闭的看盘入口，看整体态势后可直接下钻台账或发起新偏差
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button icon={<ReloadOutlined />} loading={isRefreshing} onClick={handleRefresh}>
            刷新
          </Button>
          <Link href="/quality/deviation/new">
            <Button type="primary" icon={<PlusOutlined />}>
              新建偏差
            </Button>
          </Link>
        </div>
      </header>

      {initialStatistics === null && (
        <Alert
          type="warning"
          showIcon
          title="统计数据暂时不可用"
          description="后端统计接口未返回数据，下方看盘为空态。可点击右上「刷新」重试，或先进入偏差台账查看明细。"
        />
      )}

      <DeviationStatCards statistics={initialStatistics} loading={isRefreshing} />

      <DeviationDistributionCharts statistics={initialStatistics} />

      <div className="flex items-start gap-2 rounded-xl border border-[var(--color-hairline-soft)] bg-[var(--color-surface-soft)] px-4 py-3">
        <span className="mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--color-warning)]" />
        <p className="text-[12px] leading-5 text-[var(--color-slate)]">{DEVIATION_OVERDUE_HINT}</p>
      </div>
    </div>
  )
}