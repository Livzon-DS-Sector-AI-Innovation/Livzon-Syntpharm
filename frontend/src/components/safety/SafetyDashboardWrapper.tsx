'use client'

import dynamic from 'next/dynamic'
import type { DashboardData } from './SafetyDashboard'

const SafetyDashboard = dynamic(() => import('./SafetyDashboard'), { ssr: false })

export default function SafetyDashboardWrapper({ data }: { data: DashboardData }) {
  return <SafetyDashboard data={data} />
}
