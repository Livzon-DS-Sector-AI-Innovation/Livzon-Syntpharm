import { getCurrentUser } from '@/actions/auth'
import { ModuleSettingsClient, NoAccessResult } from '@/components/settings'
import { PERM } from '@/lib/permissions/codes'
import { hasPermission } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

export default async function AgentSettingsPage() {
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
      moduleCode="agent"
      moduleName="智能体"
      moduleDescription="配置 PPT 配音视频的旁白、逐段合成节奏与页内视觉引导（讲到哪、画面就亮到哪）。"
    />
  )
}