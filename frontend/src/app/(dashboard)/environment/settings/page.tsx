import { ModuleSettingsPage } from '@/components/module-settings'

export const dynamic = 'force-dynamic'

/** 环保管理 · 模块配置（权限管理 + 本模块其他配置）。准入：environment:admin:read */
export default function EnvironmentSettingsPage() {
  return <ModuleSettingsPage moduleCode="environment" />
}
