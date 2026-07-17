'use client'

import dynamic from 'next/dynamic'
import type { PurchaseRequestCategory, PurchaseApprovalRole, PurchaseRequestResponse } from '@/types/procurement'

const PurchaseApprovalClient = dynamic(
  () => import('./PurchaseApprovalClient').then(mod => ({ default: mod.PurchaseApprovalClient })),
  { ssr: false }
)

type PurchaseApprovalClientWrapperProps = {
  category: PurchaseRequestCategory
  categoryLabel: string
  approvalRole: PurchaseApprovalRole
  initialRequests: PurchaseRequestResponse[]
  initialTotal: number
}

export default function PurchaseApprovalClientWrapper(props: PurchaseApprovalClientWrapperProps) {
  return <PurchaseApprovalClient {...props} />
}
