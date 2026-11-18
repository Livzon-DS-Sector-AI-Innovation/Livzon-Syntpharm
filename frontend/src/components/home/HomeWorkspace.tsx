'use client'

import Link from 'next/link'
import { Empty, Typography } from 'antd'
import { ArrowRightOutlined } from '@ant-design/icons'
import { ModuleIcon } from '@/components/Icons'
import { UserAvatar } from '@/components/common/UserAvatar'
import { ProcessPanel } from './ProcessPanel'
import { TodoPanel } from './TodoPanel'
import type { WorkbenchOverview } from '@/lib/api/server/workbench'
import type { components } from '@/types/generated/schema'

const { Text, Title } = Typography

export interface HomeModuleEntry {
  key: string
  label: string
  icon: string
  path: string
}

interface HomeWorkspaceProps {
  userName: string
  /** 当前登录用户的飞书头像（可选，缺省走首字母兜底） */
  avatarUrl?: string | null
  department?: string | null
  position?: string | null
  /** 服务端格式化好的日期，避免客户端/服务端时区差异导致 hydration 不一致 */
  today: string
  modules: HomeModuleEntry[]
  /** 工作台聚合数据；null = 取数失败，两块卡片降级为「数据暂时不可用」 */
  overview: WorkbenchOverview | null
}

type TodoSection = components['schemas']['TodoSectionModel']
type ProcessSection = components['schemas']['ProcessSectionModel']

const EMPTY_TODOS: TodoSection = {
  total: 0,
  unread_total: 0,
  has_more: false,
  person_total: 0,
  role_total: 0,
  groups: [],
}
const EMPTY_PROCESSES: ProcessSection = { total: 0, has_more: false, groups: [] }

/**
 * 登录后的默认首页（工作台）。
 *
 * 数据全部来自服务端已算好的权限视图与工作台聚合接口，不在客户端二次请求：
 * - 快捷入口 = 当前账号可见的模块，右上角显示该模块待办数（0 不显示）；
 * - 审核待办 / 我参与的流程 = `GET /api/v1/workbench/overview`。
 */
export function HomeWorkspace({
  userName,
  avatarUrl,
  department,
  position,
  today,
  modules,
  overview,
}: HomeWorkspaceProps) {
  const meta = [today, department, position].filter(Boolean).join(' · ')
  const todos = overview?.todos ?? EMPTY_TODOS
  const processes = overview?.processes ?? EMPTY_PROCESSES

  const todoBadgeByModule = new Map<string, { count: number; hasMore: boolean }>()
  for (const group of todos.groups ?? []) {
    todoBadgeByModule.set(group.module_key, { count: group.count, hasMore: group.has_more })
  }

  const summary = [
    { key: 'todos', label: '待审批', value: todos.total, more: todos.has_more, anchor: 'home-todos' },
    { key: 'processes', label: '我参与的流程', value: processes.total, more: processes.has_more, anchor: 'home-processes' },
  ]

  const degraded = (overview?.degraded_sources?.length ?? 0) > 0

  return (
    <div className="mx-auto max-w-[1200px] space-y-4">
      <h1 className="sr-only">工作台</h1>

      <section className="rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-6">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-4">
            <UserAvatar size={52} name={userName} src={avatarUrl} />
            <div className="min-w-0">
              <Title level={3} style={{ margin: 0 }}>
                {userName}，欢迎回来
              </Title>
              <Text type="secondary">{meta}</Text>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {summary.map((entry) => (
              <button
                key={entry.key}
                type="button"
                onClick={() =>
                  document.getElementById(entry.anchor)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
                }
                className="flex cursor-pointer items-baseline gap-1.5 rounded-[var(--rounded-md)] border border-[var(--color-hairline)] px-3 py-1.5 transition-colors hover:border-[var(--color-primary)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]"
              >
                <span className="text-[12px] text-[var(--color-steel)]">{entry.label}</span>
                <span className="text-[15px] font-semibold text-[var(--color-primary)]">
                  {entry.value}
                  {entry.more ? '+' : ''}
                </span>
              </button>
            ))}
          </div>
        </div>
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
            {modules.map((mod) => {
              const todoBadge = todoBadgeByModule.get(mod.key)
              return (
                <Link
                  key={mod.key}
                  href={mod.path}
                  className="group flex items-center gap-3 rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-4 transition-colors hover:border-[var(--color-primary)]"
                >
                  <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--rounded-md)] bg-[var(--color-surface)] text-[var(--color-primary)]">
                    <ModuleIcon name={mod.icon} className="h-5 w-5" />
                  </span>
                  <span className="min-w-0 flex-1 truncate text-[14px] font-medium text-[var(--color-ink)]">
                    {mod.label}
                  </span>
                  {todoBadge && todoBadge.count > 0 && (
                    <span
                      className="flex h-5 min-w-5 shrink-0 items-center justify-center rounded-[6px] bg-[var(--color-primary)] px-1.5 text-[11px] font-semibold text-white"
                      title={`${todoBadge.count} 项以上待办`}
                    >
                      {todoBadge.count > 99 ? '99+' : `${todoBadge.count}${todoBadge.hasMore ? '+' : ''}`}
                    </span>
                  )}
                  <ArrowRightOutlined className="text-[var(--color-steel)] opacity-0 transition-opacity group-hover:opacity-100" />
                </Link>
              )
            })}
          </div>
        )}
      </section>

      {degraded && (
        <div className="rounded-[var(--rounded-md)] border border-[var(--color-hairline)] bg-[var(--color-surface-soft)] px-3 py-2 text-[12px] text-[var(--color-steel)]">
          部分待办数据暂时不可用，已展示可用部分；请稍后刷新。
        </div>
      )}

      <div className="grid items-start gap-3 md:grid-cols-2">
        <TodoPanel section={todos} unavailable={overview === null} />
        <ProcessPanel section={processes} unavailable={overview === null} />
      </div>
    </div>
  )
}