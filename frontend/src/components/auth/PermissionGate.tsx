'use client'

import type { ReactNode } from 'react'
import { usePermission } from '@/hooks/usePermission'
import type { PermissionCode } from '@/lib/permissions/codes'

interface PermissionGateProps {
  code: PermissionCode
  children: ReactNode
}

/**
 * 按钮级权限门：无权限时**什么都不渲染**（按钮直接不出现）。
 *
 * 用法：
 *   <PermissionGate code={PERM.configManage}>
 *     <Button type="primary">新建字典</Button>
 *   </PermissionGate>
 *
 * 两个细节：
 * 1. 权限还在加载（loading）时同样不渲染 —— 否则会「先显示按钮、权限到位后再消失」。
 * 2. 内部走 usePermission（React Query 缓存），页面里放多少个门都只请求一次权限。
 *
 * 注意：前端隐藏只是体验优化，后端 require_permission 仍会拦截绕过前端的调用。
 */
export function PermissionGate({ code, children }: PermissionGateProps) {
  const { can, loading } = usePermission()

  if (loading || !can(code)) {
    return null
  }

  return <>{children}</>
}
