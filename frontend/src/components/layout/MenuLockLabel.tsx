'use client'

import { LockOutlined } from '@ant-design/icons'

/**
 * 「无权限」菜单项的统一外观：文案 + 锁图标。
 *
 * 侧栏菜单、顶部模块 Tab、移动端模块下拉三处都要表达「能点进去，但进去是无权限页」，
 * 以前各写一份（侧栏与顶栏的灰度实现还不一致），统一到这一个组件。
 */
export function MenuLockLabel({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      {label}
      <LockOutlined className="text-[11px]" aria-label="无权限" />
    </span>
  )
}
