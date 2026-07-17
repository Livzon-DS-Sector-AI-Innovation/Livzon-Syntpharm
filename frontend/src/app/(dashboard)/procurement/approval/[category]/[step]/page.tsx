import { notFound } from 'next/navigation'
import PurchaseApprovalClientWrapper from '@/components/procurement/PurchaseApprovalClientWrapper'
import { fetchPurchaseRequests } from '@/lib/api/server/procurement'
import type { PurchaseApprovalRole, PurchaseRequestCategory } from '@/types/procurement'
import { approvalStepToRole, purchaseCategoryLabels } from '@/components/procurement/purchaseRequestConstants'

export const dynamic = 'force-dynamic'

const DEFAULT_PAGE_SIZE = 20

interface PurchaseApprovalPageProps {
  params: Promise<{ category: string; step: string }>
}

export function generateStaticParams() {
  return Object.keys(purchaseCategoryLabels).flatMap((category) =>
    Object.keys(approvalStepToRole).map((step) => ({ category, step }))
  )
}

export default async function PurchaseApprovalPage({
  params,
}: PurchaseApprovalPageProps) {
  const { category, step } = await params
  const categoryLabel = purchaseCategoryLabels[category as PurchaseRequestCategory]
  const approvalRole = approvalStepToRole[step as keyof typeof approvalStepToRole]

  if (!categoryLabel || !approvalRole) {
    notFound()
  }

  const response = await fetchPurchaseRequests({
    category: category as PurchaseRequestCategory,
    approval_role: approvalRole as PurchaseApprovalRole,
    approval_view: 'pending',
    page: 1,
    page_size: DEFAULT_PAGE_SIZE,
  }).catch(() => ({
    code: 200,
    message: 'success',
    data: [],
    meta: {
      page: 1,
      page_size: DEFAULT_PAGE_SIZE,
      total: 0,
    },
  }))

  return (
    <PurchaseApprovalClientWrapper
      category={category as PurchaseRequestCategory}
      categoryLabel={categoryLabel}
      approvalRole={approvalRole as PurchaseApprovalRole}
      initialRequests={response.data}
      initialTotal={Number(response.meta?.total ?? response.data.length)}
    />
  )
}
