import TrainingSpecialistsClient from '@/components/hr/TrainingSpecialistsClient'

export default function TrainingSpecialistsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold text-[var(--color-charcoal)] mb-2">
          培训专员管理
        </h1>
        <p className="text-[14px] text-[var(--color-steel)]">
          维护各部门的培训专员信息
        </p>
      </div>
      <TrainingSpecialistsClient />
    </div>
  )
}
