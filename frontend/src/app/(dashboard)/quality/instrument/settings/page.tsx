import { redirect } from 'next/navigation'

export const dynamic = 'force-dynamic'

/**
 * 仪器提醒设置已迁移到「模块配置」页签。
 * 保留旧地址做重定向，确保书签与外部链接不断（不留双入口）。
 */
export default function InstrumentSettingsRedirect() {
  redirect('/quality/settings?tab=instrument')
}
