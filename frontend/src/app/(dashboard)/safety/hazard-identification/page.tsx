import { Suspense } from "react"
import { WorkflowListPanel } from '@/components/safety'

export default function HazardIdentificationPage() {
  return (
    <Suspense fallback={null}>
      <WorkflowListPanel />
    </Suspense>
  )
}
