import { ModuleSettingsPage } from '@/components/module-settings'

export const dynamic = 'force-dynamic'

/** 行政管理 · 模块配置（权限管理 + 本模块其他配置）。准入：administration:admin:read */
export default function AdministrationSettingsPage() {
  return <ModuleSettingsPage moduleCode="administration" />
}
