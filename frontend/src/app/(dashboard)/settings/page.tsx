import { Result } from 'antd'
import { getCurrentUser } from '@/actions/auth'
import SettingsAdminClient from '@/components/settings/SettingsAdminClient'

export const dynamic = 'force-dynamic'

export default async function SettingsPage() {
  const user = await getCurrentUser()

  if (!user) {
    return (
      <Result
        status="403"
        title="无权访问"
        subTitle="只有管理员可以管理用户、LLM 模型配置与 Livzon Skill。"
      />
    )
  }

  return <SettingsAdminClient />
}
