import { ModuleSettingsPage } from '@/components/module-settings'

export const dynamic = 'force-dynamic'

/** 采购管理 · 模块配置（权限管理 + 本模块其他配置）。准入：procurement:admin:read */
export default function ProcurementSettingsPage() {
  return <ModuleSettingsPage moduleCode="procurement" />
}
