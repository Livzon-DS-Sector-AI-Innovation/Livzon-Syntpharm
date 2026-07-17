'use client'

import dynamic from 'next/dynamic'

const SpecialOpsPersonnelPanel = dynamic(() => import('./SpecialOpsPersonnelPanel'), {
  ssr: false,
  loading: () => <div style={{ padding: 20 }}>加载中...</div>
})

export default function SpecialOpsPersonnelPanelWrapper() {
  return <SpecialOpsPersonnelPanel />
}
