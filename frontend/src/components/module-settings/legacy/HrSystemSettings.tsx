'use client'

import { SystemSettingsClient } from '@/components/hr'

/** 原 `/hr/system/settings` 页的客户端实现，迁移到 `/hr/settings?tab=feishu` 页签后复用。 */
export default function HrSystemSettings() {
  return (
    <div className="space-y-4">
      <SystemSettingsClient />
    </div>
  )
}
