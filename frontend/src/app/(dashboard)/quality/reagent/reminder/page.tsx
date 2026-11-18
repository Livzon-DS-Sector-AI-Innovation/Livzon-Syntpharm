import { redirect } from 'next/navigation'

export const dynamic = 'force-dynamic'

/** 试剂库存提醒已迁移到「模块配置」页签，旧地址重定向。 */
export default function ReagentReminderRedirect() {
  redirect('/quality/settings?tab=reagent')
}
