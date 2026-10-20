'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { Tag } from 'antd'
import {
  ArrowRightOutlined,
  AuditOutlined,
  ControlOutlined,
  LoginOutlined,
  MenuOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  TeamOutlined,
  ToolOutlined,
} from '@ant-design/icons'

export interface SettingsOverviewEntry {
  key: string
  title: string
  description: string
  path: string
  icon: 'team' | 'security' | 'login' | 'audit' | 'config' | 'menu' | 'ops'
  /** 是否具备该功能的管理权限（否则为只读） */
  manageable: boolean
}

export interface SettingsOverviewGroup {
  key: string
  title: string
  items: SettingsOverviewEntry[]
}

const ICONS: Record<SettingsOverviewEntry['icon'], ReactNode> = {
  team: <TeamOutlined />,
  security: <SafetyCertificateOutlined />,
  login: <LoginOutlined />,
  audit: <AuditOutlined />,
  config: <SettingOutlined />,
  menu: <MenuOutlined />,
  ops: <ToolOutlined />,
}

/**
 * 系统管理概览：按当前账号权限渲染的功能入口。
 *
 * 只展示服务端已过滤好的条目，客户端不再做权限判断 ——
 * 避免出现「先渲染全部卡片、拿到权限后再消失」的闪烁。
 */
export function SettingsOverviewClient({ groups }: { groups: SettingsOverviewGroup[] }) {
  return (
    <div className="space-y-6">
      {groups.map((group) => (
        <section key={group.key}>
          <div className="mb-3 flex items-center gap-2">
            <span className="text-[15px] font-semibold text-[var(--color-ink)]">{group.title}</span>
            <Tag className="!m-0 !text-[11px]">{group.items.length}</Tag>
          </div>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-3">
            {group.items.map((item) => (
              <Link
                key={item.key}
                href={item.path}
                className="group flex items-start gap-3 rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-4 transition-colors hover:border-[var(--color-primary)]"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--rounded-md)] bg-[var(--color-surface)] text-[var(--color-primary)]">
                  {ICONS[item.icon] ?? <ControlOutlined />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[14px] font-medium text-[var(--color-ink)]">
                      {item.title}
                    </span>
                    <Tag
                      color={item.manageable ? 'blue' : 'default'}
                      className="!m-0 !text-[11px]"
                    >
                      {item.manageable ? '可管理' : '仅查看'}
                    </Tag>
                  </div>
                  <p className="m-0 mt-1 text-[12px] leading-5 text-[var(--color-steel)]">
                    {item.description}
                  </p>
                </div>
                <ArrowRightOutlined className="mt-2 shrink-0 text-[var(--color-steel)] opacity-0 transition-opacity group-hover:opacity-100" />
              </Link>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
