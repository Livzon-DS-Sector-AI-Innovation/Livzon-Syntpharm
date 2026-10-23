'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Spin, Tabs } from 'antd'
import GrantManagementClient from './GrantManagementClient'
import PermissionCatalogClient from './PermissionCatalogClient'
import RoleManagementClient from './RoleManagementClient'
import { SettingsPageHeader } from './SettingsPageHeader'
import { usePermission } from '@/hooks/usePermission'
import { PERM } from '@/lib/permissions/codes'

const TAB_KEYS = ['roles', 'grants', 'permissions'] as const
type TabKey = (typeof TAB_KEYS)[number]

/**
 * 权限管理（角色 / 授权 / 权限目录）。
 *
 * 每个 Tab 按自身权限码过滤（而非只按页面守卫的 `role:read`）：
 * - 角色管理   → `platform:role:read`
 * - 授权管理   → `platform:grant:read`
 * - 权限目录   → `platform:permission:read`
 *
 * 否则「只有 role:read」的用户能进页面，却在授权管理 / 权限目录 Tab 里遇到接口 403 报错。
 *
 * 支持 `?tab=grants` 直达指定 Tab；若指定 Tab 无权限，回退到第一个可见 Tab。
 */
export default function PermissionAdminClient({ initialTab }: { initialTab?: string }) {
  const router = useRouter()
  const { can, loading } = usePermission()

  const tabs = useMemo(
    () =>
      [
        { key: 'roles', label: '角色管理', children: <RoleManagementClient />, visible: can(PERM.roleRead) },
        {
          key: 'grants',
          label: '授权管理',
          children: <GrantManagementClient />,
          // 有 grant:manage 必然需要进入授权管理（只读列表接口同样接受 manage）
          visible: can(PERM.grantRead) || can(PERM.grantManage),
        },
        { key: 'permissions', label: '权限目录', children: <PermissionCatalogClient />, visible: can(PERM.permissionRead) },
      ].filter((t) => t.visible),
    [can],
  )

  const visibleKeys = useMemo(() => tabs.map((t) => t.key), [tabs])

  const [activeKey, setActiveKey] = useState<TabKey>(
    TAB_KEYS.includes(initialTab as TabKey) ? (initialTab as TabKey) : 'roles',
  )

  // 派生当前激活 Tab：若 activeKey 不在可见集合内（如无权限的 ?tab= 直达，或权限尚未加载），
  // 落到第一个可见 Tab，避免在 effect 里 setState。
  const effectiveKey = visibleKeys.includes(activeKey)
    ? activeKey
    : ((visibleKeys[0] as TabKey) ?? 'roles')

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Spin />
      </div>
    )
  }

  return (
    <div className="settings-scope settings-enter mx-auto max-w-[1320px] md:px-6 md:py-6">
            <SettingsPageHeader
              title="权限管理"
              description="管理角色、用户授权与数据范围、权限目录与接口绑定登记簿。"
            />
            <Tabs
        activeKey={effectiveKey}
        onChange={(key) => {
          setActiveKey(key as TabKey)
          router.replace(`/settings/permission?tab=${key}`, { scroll: false })
        }}
        items={tabs}
      />
    </div>
  )
}
