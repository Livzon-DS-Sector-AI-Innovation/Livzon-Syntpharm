import { ModuleSettingsPage } from '@/components/module-settings'

export const dynamic = 'force-dynamic'

/** 设备管理 · 模块配置（权限管理 + 本模块其他配置）。准入：equipment:admin:read */
export default function EquipmentSettingsPage() {
  return <ModuleSettingsPage moduleCode="equipment" />
}
