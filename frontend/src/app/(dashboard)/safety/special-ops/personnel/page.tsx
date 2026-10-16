import SpecialOpsPersonnelPanel from '@/components/safety/SpecialOpsPersonnelPanel'

export const dynamic = 'force-dynamic'

export default function SpecialOpsPersonnelPage() {
  return (
    <>
      <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-4">作业人员</h1>
      <SpecialOpsPersonnelPanel />
    </>
  )
}
