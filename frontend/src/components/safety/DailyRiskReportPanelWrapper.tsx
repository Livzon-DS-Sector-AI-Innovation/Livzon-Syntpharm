'use client'

import dynamic from 'next/dynamic'

const DailyRiskReportPanel = dynamic(() => import('./DailyRiskReportPanel'), {
  ssr: false,
  loading: () => <div style={{ padding: 20 }}>加载中...</div>
})

export default function DailyRiskReportPanelWrapper() {
  return <DailyRiskReportPanel />
}
