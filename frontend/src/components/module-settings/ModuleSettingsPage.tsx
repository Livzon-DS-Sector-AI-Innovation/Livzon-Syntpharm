import { getCurrentUser } from '@/actions/auth'
import { NoAccessResult, SettingsPageHeader } from '@/components/settings'
import { ADMIN_ENTRY_PERM } from '@/lib/permissions/codes'
import { getPermissionView, hasPermission } from '@/lib/permissions/server'
import ModuleSettingsTabs from './ModuleSettingsTabs'
import { getModuleSettings } from './settings-registry'

interface ModuleSettingsPageProps {
  moduleCode: string
}

/**
 * 模块配置页（服务端外壳）。
 *
 * 准入口径：`{module}:admin:read`（模块负责人 / 模块管理员持有；系统管理员不受限）。
 * 页面守卫生效后，菜单里灰显加锁的入口即使被直接输入 URL 也只会看到无权限页，
 * 不会露出任何配置内容（三道门中的第二道）。
 */
export default async function ModuleSettingsPage({ moduleCode }: ModuleSettingsPageProps) {
  const definition = getModuleSettings(moduleCode)
  if (!definition) {
    return <NoAccessResult title="页面不存在" subTitle="该模块还没有配置页。" />
  }

  const user = await getCurrentUser()
  if (!user) {
    return <NoAccessResult title="请先登录" subTitle="登录后即可访问模块配置。" />
  }

  const adminPerm = ADMIN_ENTRY_PERM[`${moduleCode}Admin` as keyof typeof ADMIN_ENTRY_PERM]
  if (!adminPerm) {
    // 注册表里声明了配置页、但权限码没登记：宁可拒绝，也不要用 undefined 去判权限
    return <NoAccessResult title="页面不存在" subTitle="该模块的配置入口还没有登记权限码。" />
  }

  const [view, allowed] = await Promise.all([getPermissionView(), hasPermission(adminPerm)])
  if (!allowed) {
    return (
      <NoAccessResult
        subTitle={`查看或修改「${definition.moduleLabel}」的配置需要模块管理权限。`}
        requiredPermission={adminPerm}
        moduleLabel={definition.moduleLabel}
      />
    )
  }

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6">
      <SettingsPageHeader title={`模块配置 · ${definition.moduleLabel}`} description={definition.description} />
      <ModuleSettingsTabs
        definition={definition}
        canManage={allowed}
        currentUserId={user.id}
        isSystemAdmin={view.isSuperuser}
      />
    </div>
  )
}
