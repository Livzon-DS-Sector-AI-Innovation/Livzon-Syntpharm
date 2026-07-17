import { ModuleSettingsClient } from '@/components/settings'

export default function SafetySettingsPage() {
  return (
    <ModuleSettingsClient
      moduleCode="safety"
      moduleName="安全管理"
      moduleDescription="配置安全模块的 AI 模型、飞书集成等运行时参数。API 密钥等敏感信息请在全局设置页面管理。"
    />
  )
}
