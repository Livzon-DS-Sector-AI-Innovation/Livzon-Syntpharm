import { getCurrentUser } from '@/actions/auth'
import { getModuleSettings } from '@/actions/module-settings'
import { getLLMConfigs } from '@/actions/settings'
import { ReportGenSettingsClient } from '@/components/research'
import { NoAccessResult } from '@/components/settings'
import { fetchReportGenMetricsServer } from '@/lib/api/server/research/report-gen'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'
import type { ModuleSetting } from '@/types/module-settings'
import { REPORT_GEN_METRIC_DEFAULT_WINDOW, type ReportGenMetrics } from '@/types/research/report-gen'
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

  // 指标取不到不该拖垮整个配置页：转成 null 交给面板走空态与重试
  let metrics: ReportGenMetrics | null = null
  try {
    metrics = await fetchReportGenMetricsServer(REPORT_GEN_METRIC_DEFAULT_WINDOW)
  } catch {
    metrics = null
  }

  return (
    <ReportGenSettingsClient
      settings={settings}
      llmConfigs={llmConfigs}
      canManage={canManage}
      initialMetrics={metrics}
    />
  )
}