import { ModuleSettingsClient } from '@/components/settings'

export default function EnergySettingsPage() {
  return (
    <ModuleSettingsClient
      moduleCode="energy"
      moduleName="能源管理"
      moduleDescription="配置能源模块的自动采集功能开关。"
    />
  )
}
