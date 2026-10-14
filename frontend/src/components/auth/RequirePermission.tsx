'use client'

import type { ReactNode } from 'react'
import { Skeleton } from 'antd'
import { usePermission } from '@/hooks/usePermission'
import { NoAccessResult } from '@/components/settings/NoAccessResult'
import type { PermissionCode } from '@/lib/permissions/codes'

interface RequirePermissionProps {
  code: PermissionCode
  children: ReactNode
}

/**
 * 页面级权限守卫（客户端）。
 *
 * 无权限时渲染「当前用户权限不足」而不是让子组件去请求接口撞 403。
 * 服务端页面（RSC）优先用 lib/permissions/server.ts 的 hasPermission()，
 * 那样没有 loading 骨架的闪烁。
 */
export function RequirePermission({ code, children }: RequirePermissionProps) {
  const { can, loading } = usePermission()

  if (loading) {
    return <Skeleton active paragraph={{ rows: 6 }} />
  }

  if (!can(code)) {
    return <NoAccessResult />
  }

  return <>{children}</>
}
