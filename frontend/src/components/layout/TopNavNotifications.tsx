'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { App, Dropdown, Empty, Skeleton } from 'antd'
import { CheckOutlined, ReloadOutlined } from '@ant-design/icons'
import { BellIcon } from '@/components/Icons'
import { WorkbenchItemRow } from '@/components/home'
import { markAllTodosRead, markTodoRead, type TodoReadMark } from '@/actions/workbench'
import {
  fetchWorkbenchTodos,
  flattenTodoItems,
  type FlatTodoItem,
  type WorkbenchTodoSnapshot,
} from '@/lib/api/client/workbench'

/** 角标数字上限：超过后统一「99+」，避免挤占顶栏 */
const BADGE_MAX = 99
const QUERY_KEY = ['workbench-todos-badge'] as const

function itemKey(item: FlatTodoItem): string {
  return `${item.source}:${item.id}`
}

function toReadMark(item: FlatTodoItem): TodoReadMark {
  return { source: item.source, item_id: item.id, fingerprint: item.fingerprint }
}

/**
 * 顶栏消息提醒：铃铛 + 工作台待办弹层。
 *
 * 数据源是工作台聚合接口（免权限码，按用户有效权限逐数据源门控）。
 * 已读状态由后端按内容指纹持久化：点击条目 / 「标为已读」只影响角标，
 * 单据状态或环节变化后会自动重新计入未读（见 platform/workbench/read_marks.py）。
 */
export function TopNavNotifications() {
  const [open, setOpen] = useState(false)
  const [markingAll, setMarkingAll] = useState(false)
  const queryClient = useQueryClient()
  const { message } = App.useApp()

  const { data, isLoading, isError, isFetching, refetch } = useQuery({
    queryKey: QUERY_KEY,
    queryFn: () => fetchWorkbenchTodos(5),
    // 提醒数据不需要秒级实时：1 分钟内重复打开直接复用缓存
    staleTime: 60_000,
    // 全局默认关闭了回窗刷新，这里按「提醒」语义单独打开
    refetchOnWindowFocus: true,
  })

  const todos = data?.todos
  const total = todos?.total ?? 0
  const unread = todos?.unread_total ?? 0
  const hasMore = todos?.has_more ?? false
  const degradedSources = data?.degradedSources ?? []
  const items = useMemo(() => (todos ? flattenTodoItems(todos) : []), [todos])
  const unreadItems = useMemo(
    () => items.filter((item) => !item.is_read && item.fingerprint),
    [items],
  )

  const badgeText = unread > BADGE_MAX ? `${BADGE_MAX}+` : hasMore ? `${unread}+` : String(unread)

  /** 乐观更新：把指定条目置为已读并同步扣减未读数（服务端真值随后由 invalidate 覆盖） */
  const applyOptimisticRead = (keys: Set<string>) => {
    if (keys.size === 0) return
    queryClient.setQueryData<WorkbenchTodoSnapshot>(QUERY_KEY, (previous) => {
      if (!previous) return previous
      let nextUnread = previous.todos.unread_total ?? 0
      const groups = (previous.todos.groups ?? []).map((group) => ({
        ...group,
        items: (group.items ?? []).map((item) => {
          if (item.is_read || !keys.has(`${item.source}:${item.id}`)) return item
          nextUnread = Math.max(0, nextUnread - 1)
          return { ...item, is_read: true }
        }),
      }))
      return {
        ...previous,
        todos: { ...previous.todos, groups, unread_total: nextUnread },
      }
    })
  }

  const refreshAfterMutation = () => {
    void queryClient.invalidateQueries({ queryKey: QUERY_KEY })
  }

  const markOne = (item: FlatTodoItem) => {
    if (item.is_read || !item.fingerprint) return
    applyOptimisticRead(new Set([itemKey(item)]))
    void markTodoRead(toReadMark(item))
      .catch(() => message.error('标记已读失败，请稍后重试'))
      .finally(refreshAfterMutation)
  }

  const markAll = () => {
    if (unreadItems.length === 0 || markingAll) return
    setMarkingAll(true)
    applyOptimisticRead(new Set(unreadItems.map(itemKey)))
    void markAllTodosRead(unreadItems.map(toReadMark))
      .catch(() => message.error('一键已读失败，请稍后重试'))
      .finally(() => {
        setMarkingAll(false)
        refreshAfterMutation()
      })
  }

  const handleOpenChange = (next: boolean) => {
    setOpen(next)
    // 打开时强制取一次最新数据：缓存可能是几分钟前进入页面时拉的
    if (next) void refetch()
  }

  // 宽度随视口收缩：弹层右对齐铃铛按钮（铃铛右侧还有 48px 的头像按钮），
  // 固定 360px 在窄屏会被左边裁掉；`100vw - 88px` 让左右各留约 20px。
  const panelWidth = 'min(360px, calc(100vw - 88px))'

  const panel = (
    <div
      className="overflow-hidden rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] shadow-lg"
      style={{ width: panelWidth }}
    >
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-hairline)] px-4 py-3">
        <div className="flex items-baseline gap-2">
          <span className="text-[14px] font-semibold text-[var(--color-ink)]">待办提醒</span>
          {!isError && (
            <span className="text-[12px] text-[var(--color-steel)]">
              未读 {unread} / 共 {total}
              {hasMore ? '+' : ''}
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={markAll}
            disabled={unread === 0 || markingAll}
            className="flex items-center gap-1 text-[12px] text-[var(--color-steel)] transition-colors hover:text-[var(--color-primary)] disabled:cursor-default disabled:opacity-40"
          >
            <CheckOutlined />
            全部已读
          </button>
          <button
            type="button"
            onClick={() => void refetch()}
            disabled={isFetching}
            className="flex items-center gap-1 text-[12px] text-[var(--color-steel)] transition-colors hover:text-[var(--color-primary)] disabled:opacity-50"
          >
            <ReloadOutlined spin={isFetching} />
            刷新
          </button>
        </div>
      </div>

      <div className="max-h-[360px] overflow-y-auto">
        {degradedSources.length > 0 && (
          <p className="border-b border-[var(--color-hairline-soft)] bg-[var(--color-surface)] px-4 py-2 text-[12px] text-[var(--color-warning)]">
            部分数据源暂不可用，待办可能不完整
          </p>
        )}

        {isLoading ? (
          <div className="px-4 py-3">
            <Skeleton active title={false} paragraph={{ rows: 4 }} />
          </div>
        ) : isError ? (
          <div className="px-4 py-6 text-center">
            <p className="text-[12px] text-[var(--color-steel)]">待办数据暂时不可用</p>
            <button
              type="button"
              onClick={() => void refetch()}
              className="mt-2 text-[12px] text-[var(--color-primary)] hover:underline"
            >
              点击重试
            </button>
          </div>
        ) : items.length === 0 ? (
          <div className="px-4 py-4">
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待办" />
          </div>
        ) : (
          <div className="p-1">
            {items.map((item) => {
              const read = Boolean(item.is_read)
              return (
                <div
                  key={`${item.source}-${item.id}`}
                  onClick={() => {
                    markOne(item)
                    // 有详情页的条目点击即跳转，顺便收起弹层；无页面条目保留弹层看「已读」态
                    if (item.path) setOpen(false)
                  }}
                >
                  <WorkbenchItemRow
                    item={item}
                    variant="todo"
                    isRead={read}
                    actionSlot={
                      read ? undefined : (
                        <button
                          type="button"
                          data-read-action
                          onClick={(event) => {
                            event.preventDefault()
                            event.stopPropagation()
                            markOne(item)
                          }}
                          className="pointer-events-none rounded-[4px] border border-[var(--color-hairline-strong)] bg-[var(--color-canvas)] px-2 py-1 text-[11px] text-[var(--color-steel)] opacity-0 transition-opacity hover:border-[var(--color-primary)] hover:text-[var(--color-primary)] focus-visible:pointer-events-auto focus-visible:opacity-100 group-hover:pointer-events-auto group-hover:opacity-100"
                        >
                          标为已读
                        </button>
                      )
                    }
                  />
                </div>
              )
            })}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-[var(--color-hairline)] px-4 py-2">
        <span className="text-[12px] text-[var(--color-steel)]">
          {todos && todos.person_total > 0 ? `待我审批 ${todos.person_total} 项` : '按权限汇总'}
        </span>
        <Link
          href="/home"
          onClick={() => setOpen(false)}
          className="text-[12px] text-[var(--color-primary)] hover:underline"
        >
          查看全部待办 →
        </Link>
      </div>
    </div>
  )

  return (
    <Dropdown
      open={open}
      onOpenChange={handleOpenChange}
      trigger={['click']}
      placement="bottomRight"
      popupRender={() => panel}
    >
      <button
        type="button"
        aria-label={unread > 0 ? `消息提醒，${badgeText} 条未读` : '消息提醒'}
        title="待办提醒"
        className="relative flex h-8 w-8 items-center justify-center rounded-[var(--rounded-sm)] text-[var(--color-steel)] transition-colors hover:bg-[var(--color-surface)] hover:text-[var(--color-charcoal)]"
      >
        <BellIcon className="h-[18px] w-[18px]" />
        {unread > 0 && (
          <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-[var(--color-error)] px-1 text-[10px] font-medium leading-none text-white">
            {badgeText}
          </span>
        )}
      </button>
    </Dropdown>
  )
}