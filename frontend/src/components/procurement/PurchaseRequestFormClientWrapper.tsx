'use client'

import dynamic from 'next/dynamic'
import type { PurchaseRequestCategory, PurchaseRequestResponse } from '@/types/procurement'

const PurchaseRequestFormClient = dynamic(
  () => import('./PurchaseRequestFormClient').then(mod => ({ default: mod.PurchaseRequestFormClient })),
  { ssr: false }
)

type PurchaseRequestFormClientWrapperProps = {
  category: PurchaseRequestCategory
  categoryLabel: string
  initialRequests: PurchaseRequestResponse[]
  initialTotal: number
}

export default function PurchaseRequestFormClientWrapper(props: PurchaseRequestFormClientWrapperProps) {
  return <PurchaseRequestFormClient {...props} />
}
