import ModuleSettingsPage from '@/components/module-settings/ModuleSettingsPage'

export const dynamic = 'force-dynamic'

/** 能源管理 · 模块配置（权限管理 + 本模块其他配置）。准入：energy:admin:read */
export default function EnergySettingsPage() {
  return <ModuleSettingsPage moduleCode="energy" />
}
