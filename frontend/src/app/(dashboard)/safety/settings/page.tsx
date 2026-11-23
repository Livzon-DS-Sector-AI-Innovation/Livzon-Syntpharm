import { ModuleSettingsPage } from '@/components/module-settings'

export const dynamic = 'force-dynamic'

/** 安全管理 · 模块配置（权限管理 + 本模块其他配置）。准入：safety:admin:read */
export default function SafetySettingsPage() {
  return <ModuleSettingsPage moduleCode="safety" />
}
