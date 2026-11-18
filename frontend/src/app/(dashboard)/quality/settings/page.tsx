import ModuleSettingsPage from '@/components/module-settings/ModuleSettingsPage'

export const dynamic = 'force-dynamic'

/** 质量管理 · 模块配置（权限管理 + 本模块其他配置）。准入：quality:admin:read */
export default function QualitySettingsPage() {
  return <ModuleSettingsPage moduleCode="quality" />
}
