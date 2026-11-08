import { getCurrentUser } from '@/actions/auth'
import { getModuleSettings } from '@/actions/module-settings'
import { getLLMConfigs } from '@/actions/settings'
import { ReportGenSettingsClient } from '@/components/research'
import { NoAccessResult } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'
import type { ModuleSetting } from '@/types/module-settings'
import type { LLMConfig } from '@/types/settings'

export const dynamic = 'force-dynamic'

export const metadata = { title: '报告生成配置' }

export default async function ReportGenSettingsPage() {
  const user = await getCurrentUser()
  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可调整报告生成的模型与工具。" />
  }
  if (!(await hasPermission(PERM.moduleSettingRead))) {
    return <NoAccessResult title="无权查看报告生成配置" subTitle="需要「模块配置查看」权限，请联系系统管理员分配。" />
  }

  const canManage = await hasPermission(PERM.moduleSettingManage)

  let settings: ModuleSetting[] = []
  let llmConfigs: LLMConfig[] = []
  try {
    settings = (await getModuleSettings('research')).data ?? []
  } catch {
    settings = []
  }
  try {
    llmConfigs = (await getLLMConfigs('text')).data ?? []
  } catch {
    llmConfigs = []
  }

  return <ReportGenSettingsClient settings={settings} llmConfigs={llmConfigs} canManage={canManage} />
}