import { getCurrentUser } from '@/actions/auth'
import { ModuleSettingsClient, NoAccessResult } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function SafetySettingsPage() {
  const user = await getCurrentUser()

  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可访问模块设置。" />
  }

  if (!(await hasPermission(PERM.configRead))) {
    return (
      <NoAccessResult subTitle="查看模块设置需要「平台配置查看」权限，请联系管理员为你的账号分配。" />
    )
  }

  return (
    <ModuleSettingsClient
      moduleCode="safety"
      moduleName="安全管理"
      moduleDescription="配置安全模块的 AI 模型、飞书集成等运行时参数。API 密钥等敏感信息请在全局设置页面管理。"
    />
  )
}
