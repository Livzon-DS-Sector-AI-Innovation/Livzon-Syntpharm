import { ModuleSettingsClient } from '@/components/settings'

export default function HRSettingsPage() {
  return (
    <ModuleSettingsClient
      moduleCode="hr"
      moduleName="人事管理"
      moduleDescription="配置人事模块的飞书机器人、AI 模型和系统提示词等参数。"
    />
  )
}
