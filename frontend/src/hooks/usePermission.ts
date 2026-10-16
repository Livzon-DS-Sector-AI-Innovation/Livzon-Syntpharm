'use client'

import { useCallback, useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { getCurrentUser } from '@/actions/auth'
import { fetchMyPermissions } from '@/actions/permission'
import type { User } from '@/types/user'
import type { PermissionCode } from '@/lib/permissions/codes'

/**
 * 当前用户的权限（客户端）。
 *
 * 用 React Query 做**全局共享缓存**：一页里有 N 个按钮也只请求一次
 * `my-permissions`（此前每个组件各跑一次 useEffect，会产生 N 次请求）。
 *
 * 用法：
 *   const { can, loading } = usePermission()
 *   {!loading && can(PERM.configManage) && <Button>新建</Button>}
 *
 * 注意：`loading` 为 true 时**不要渲染受权限控制的按钮**，
 * 否则会出现「先显示、拿到权限后再消失」的闪烁。
 */
export function usePermission() {
  const { data: user = null, isLoading: userLoading } = useQuery<User | null>({
    queryKey: ['current-user'],
    queryFn: () => getCurrentUser(),
    staleTime: 5 * 60_000,
  })

  const { data, isLoading: permissionLoading } = useQuery({
    queryKey: ['my-permissions'],
    queryFn: fetchMyPermissions,
    enabled: !!user,
    staleTime: 5 * 60_000,
  })

  const permissions = useMemo(() => new Set<string>(data?.permissions ?? []), [data?.permissions])
  const isSuperuser = data?.is_superuser ?? false
  const loading = userLoading || (!!user && permissionLoading)

  const can = useCallback(
    (code: PermissionCode) => isSuperuser || permissions.has(code),
    [isSuperuser, permissions],
  )

  return {
    user,
    permissions,
    isSuperuser,
    loading,
    can,
  }
}
