import ModuleSettingsPage from '@/components/module-settings/ModuleSettingsPage'

export const dynamic = 'force-dynamic'

/** 研发管理 · 模块配置（权限管理 + 本模块其他配置）。准入：research:admin:read */
export default function ResearchSettingsPage() {
  return <ModuleSettingsPage moduleCode="research" />
}
