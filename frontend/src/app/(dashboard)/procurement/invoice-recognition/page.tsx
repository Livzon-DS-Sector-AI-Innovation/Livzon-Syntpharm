import InvoiceRecognitionClientWrapper from '@/components/procurement/InvoiceRecognitionClientWrapper'

export const dynamic = 'force-dynamic'

export default function InvoiceRecognitionPage() {
  return <InvoiceRecognitionClientWrapper initialRecords={[]} initialTotal={0} />
}
