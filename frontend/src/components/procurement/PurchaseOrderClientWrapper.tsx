'use client'

import dynamic from 'next/dynamic'
import type { PurchaseOrderLineResponse } from '@/types/procurement'

const PurchaseOrderClient = dynamic(
  () => import('./PurchaseOrderClient').then(mod => ({ default: mod.PurchaseOrderClient })),
  { ssr: false }
)

type PurchaseOrderClientWrapperProps = {
  initialLines: PurchaseOrderLineResponse[]
  initialTotal: number
  initialYear: number
  initialMonth: number
}

export default function PurchaseOrderClientWrapper(props: PurchaseOrderClientWrapperProps) {
  return <PurchaseOrderClient {...props} />
}
