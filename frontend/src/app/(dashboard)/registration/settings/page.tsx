import ModuleSettingsPage from '@/components/module-settings/ModuleSettingsPage'

export const dynamic = 'force-dynamic'

/** 注册管理 · 模块配置（权限管理 + 本模块其他配置）。准入：registration:admin:read */
export default function RegistrationSettingsPage() {
  return <ModuleSettingsPage moduleCode="registration" />
}
