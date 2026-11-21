import { redirect } from 'next/navigation'

export const dynamic = 'force-dynamic'

/** 稳定性提醒设置已迁移到「模块配置」页签，旧地址重定向。 */
export default function StabilitySettingsRedirect() {
  redirect('/quality/settings?tab=stability')
}
