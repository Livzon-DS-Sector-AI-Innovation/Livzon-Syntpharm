'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Tabs } from 'antd'
import GrantManagementClient from './GrantManagementClient'
import PermissionCatalogClient from './PermissionCatalogClient'
import RoleManagementClient from './RoleManagementClient'

const TAB_KEYS = ['roles', 'grants', 'permissions'] as const
type TabKey = (typeof TAB_KEYS)[number]

/**
 * 权限管理（角色 / 授权 / 权限目录）。
 *
 * 支持 `?tab=grants` 直达指定 Tab —— 「用户管理」编辑用户时的「前往授权管理」
 * 链接会带这个参数。
 */
export default function PermissionAdminClient({ initialTab }: { initialTab?: string }) {
  const router = useRouter()
  const [activeKey, setActiveKey] = useState<TabKey>(
    TAB_KEYS.includes(initialTab as TabKey) ? (initialTab as TabKey) : 'roles',
  )

  return (
    <div className="mx-auto max-w-[1320px] px-6 py-6">
      <div className="mb-5">
        <h1 className="m-0 text-[24px] font-semibold text-[var(--color-charcoal)]">
          权限管理
        </h1>
        <p className="m-0 mt-1 text-[13px] text-[var(--color-steel)]">
          管理角色、用户授权与数据范围、权限目录与接口绑定登记簿。
        </p>
      </div>
      <Tabs
        activeKey={activeKey}
        onChange={(key) => {
          setActiveKey(key as TabKey)
          router.replace(`/settings/permission?tab=${key}`, { scroll: false })
        }}
        items={[
          {
            key: 'roles',
            label: '角色管理',
            children: <RoleManagementClient />,
          },
          {
            key: 'grants',
            label: '授权管理',
            children: <GrantManagementClient />,
          },
          {
            key: 'permissions',
            label: '权限目录',
            children: <PermissionCatalogClient />,
          },
        ]}
      />
    </div>
  )
}
