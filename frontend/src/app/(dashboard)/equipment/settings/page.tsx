import { ModuleSettingsClient } from '@/components/settings'

export default function EquipmentSettingsPage() {
  return (
    <ModuleSettingsClient
      moduleCode="equipment"
      moduleName="设备管理"
      moduleDescription="配置设备模块的飞书 WebSocket、维护计划自动生成等功能开关。"
    />
  )
}
