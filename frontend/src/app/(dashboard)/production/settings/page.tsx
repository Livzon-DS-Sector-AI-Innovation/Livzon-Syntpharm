import { ModuleSettingsPage } from '@/components/module-settings'

export const dynamic = 'force-dynamic'

/** 生产管理 · 模块配置（权限管理 + 本模块其他配置）。准入：production:admin:read */
export default function ProductionSettingsPage() {
  return <ModuleSettingsPage moduleCode="production" />
}
