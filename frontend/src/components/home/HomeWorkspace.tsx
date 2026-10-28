'use client'

import Link from 'next/link'
import { Empty, Typography } from 'antd'
import { ArrowRightOutlined } from '@ant-design/icons'
import { ModuleIcon } from '@/components/Icons'

const { Text, Title } = Typography

export interface HomeModuleEntry {
  key: string
  label: string
  icon: string
  path: string
}

interface HomeWorkspaceProps {
  userName: string
  department?: string | null
  position?: string | null
  /** 服务端格式化好的日期，避免客户端/服务端时区差异导致 hydration 不一致 */
  today: string
  modules: HomeModuleEntry[]
}

/**
 * 登录后的默认首页（工作台）。
 *
 * 内容只依赖服务端已算好的权限视图，不额外请求接口：
 * - 快捷入口 = 当前账号可见的模块（settings 落到第一个有权限的子页）
 * - 待办 / 公告暂无数据源，先显示空态，避免用假数据占位
 */
export function HomeWorkspace({
  userName,
  department,
  position,
  today,
  modules,
}: HomeWorkspaceProps) {
  const meta = [today, department, position].filter(Boolean).join(' · ')

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <h1 className="sr-only">工作台</h1>
      <section className="rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-6">
        <Title level={3} style={{ margin: 0 }}>
          {userName}，欢迎回来
        </Title>
        <Text type="secondary">{meta}</Text>
      </section>

      <section>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <span className="text-[15px] font-semibold text-[var(--color-ink)]">快捷入口</span>
          <Text type="secondary" className="text-[12px]">
            只展示你有权限访问的模块
          </Text>
        </div>

        {modules.length === 0 ? (
          <div className="rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-8">
            <Empty description="暂无可访问的模块" />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-4">
            {modules.map((mod) => (
              <Link
                key={mod.key}
                href={mod.path}
                className="group flex items-center gap-3 rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-4 transition-colors hover:border-[var(--color-primary)]"
              >
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--rounded-md)] bg-[var(--color-surface)] text-[var(--color-primary)]">
                  <ModuleIcon name={mod.icon} className="h-5 w-5" />
                </span>
                <span className="flex-1 text-[14px] font-medium text-[var(--color-ink)]">
                  {mod.label}
                </span>
                <ArrowRightOutlined className="text-[var(--color-steel)] opacity-0 transition-opacity group-hover:opacity-100" />
              </Link>
            ))}
          </div>
        )}
      </section>

      <div className="grid gap-3 md:grid-cols-2">
        <section className="rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-5">
          <div className="mb-3 text-[15px] font-semibold text-[var(--color-ink)]">待办事项</div>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待办" />
        </section>

        <section className="rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-5">
          <div className="mb-3 text-[15px] font-semibold text-[var(--color-ink)]">系统公告</div>
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无公告" />
        </section>
      </div>
    </div>
  )
}
