'use client'

import dynamic from 'next/dynamic'
import type { SpecialOperationLedgerStats } from '@/types/safety'

const SpecialOpsManagement = dynamic(() => import('./SpecialOpsManagement'), {
  ssr: false,
  loading: () => <div style={{ padding: 20 }}>加载中...</div>
})

interface SpecialOpsManagementWrapperProps {
  initialStats?: SpecialOperationLedgerStats[]
}

export default function SpecialOpsManagementWrapper({ initialStats }: SpecialOpsManagementWrapperProps) {
  return <SpecialOpsManagement initialStats={initialStats} />
}
