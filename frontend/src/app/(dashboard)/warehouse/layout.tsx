import ModuleNoAccess from '@/components/layout/ModuleNoAccess'
import { hasModuleAccess } from '@/lib/permissions/server'

export const dynamic = 'force-dynamic'

/**
 * 模块级守卫：无「访问仓储管理」权限时，URL 直连也进不来。
 * 口径与顶部导航（`MODULE_ACCESS_PERMS`）一致，避免「看得到入口、点进去被拦」。
 */
export default async function WarehouseLayout({ children }: { children: React.ReactNode }) {
  if (!(await hasModuleAccess('warehouse'))) {
    return <ModuleNoAccess moduleName="仓储管理" />
  }
  return <>{children}</>
}
