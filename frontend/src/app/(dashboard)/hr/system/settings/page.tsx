import { redirect } from 'next/navigation'

export const dynamic = 'force-dynamic'

/** 人事系统设置（飞书 Bot 配置）已迁移到「模块配置」页签，旧地址重定向。 */
export default function HrSystemSettingsRedirect() {
  redirect('/hr/settings?tab=feishu')
}
