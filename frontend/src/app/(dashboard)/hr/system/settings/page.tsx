import { SystemSettingsClient } from '@/components/hr'

export const dynamic = 'force-dynamic'

export default function SystemSettingsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-[22px] font-semibold">系统设置</h1>
      <SystemSettingsClient />
    </div>
  )
}
