import { getCurrentUser } from '@/actions/auth'
import { ModuleSettingsClient, NoAccessResult } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function EquipmentSettingsPage() {
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
      moduleCode="equipment"
      moduleName="设备管理"
      moduleDescription="配置设备模块的飞书 WebSocket、维护计划自动生成等功能开关。"
    />
  )
}
