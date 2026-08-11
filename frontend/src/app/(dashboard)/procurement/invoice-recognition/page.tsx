import InvoiceRecognitionClientWrapper from '@/components/procurement/InvoiceRecognitionClientWrapper'

export const dynamic = 'force-dynamic'

export default function InvoiceRecognitionPage() {
  return (
    <>
      <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-2">发票识别</h1>
      <InvoiceRecognitionClientWrapper initialRecords={[]} initialTotal={0} />
    </>
  )
}
