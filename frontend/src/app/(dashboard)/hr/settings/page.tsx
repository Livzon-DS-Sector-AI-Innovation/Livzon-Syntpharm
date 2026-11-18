import ModuleSettingsPage from '@/components/module-settings/ModuleSettingsPage'

export const dynamic = 'force-dynamic'

/** 人事管理 · 模块配置（权限管理 + 本模块其他配置）。准入：hr:admin:read */
export default function HrSettingsPage() {
  return <ModuleSettingsPage moduleCode="hr" />
}
