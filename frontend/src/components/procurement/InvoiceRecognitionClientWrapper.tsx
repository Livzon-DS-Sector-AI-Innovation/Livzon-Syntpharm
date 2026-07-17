'use client'

import dynamic from 'next/dynamic'
import type { InvoiceRecognitionRecordResponse } from '@/types/procurement'

const InvoiceRecognitionClient = dynamic(
  () => import('./InvoiceRecognitionClient').then(mod => ({ default: mod.InvoiceRecognitionClient })),
  { ssr: false }
)

type InvoiceRecognitionClientWrapperProps = {
  initialRecords: InvoiceRecognitionRecordResponse[]
  initialTotal: number
  initialLoadFailed?: boolean
}

export default function InvoiceRecognitionClientWrapper(props: InvoiceRecognitionClientWrapperProps) {
  return <InvoiceRecognitionClient {...props} />
}
