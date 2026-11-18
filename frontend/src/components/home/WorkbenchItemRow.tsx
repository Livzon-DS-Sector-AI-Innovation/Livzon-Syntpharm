'use client'

import type { ReactNode } from 'react'
import Link from 'next/link'
import { ArrowRightOutlined } from '@ant-design/icons'
import type { components } from '@/types/generated/schema'

type WorkbenchItem = components['schemas']['WorkbenchItemModel']

interface WorkbenchItemRowProps {
  item: WorkbenchItem
  /** todo=待办（显示判定依据标签）；process=流程（显示我的角色） */
  variant?: 'todo' | 'process'
  /** 已读：整行降透明度 + 「已读」标签（仅顶栏待办提醒使用） */
  isRead?: boolean
  /**
   * 行内右侧的操作位（如「标为已读」）。
   *
   * 渲染在 Link 之外（绝对定位），避免 `<a>` 内嵌 `<button>` 的非法结构；
   * 传入时隐藏 hover 箭头并给右侧留出空间。
   */
  actionSlot?: ReactNode
}

const OVERDUE_COLOR = '#D97706'

function buildMeta(item: WorkbenchItem, variant: 'todo' | 'process'): string {
  const parts: string[] = []
  if (variant === 'process' && item.my_roles?.length) parts.push(item.my_roles.join(' / '))
  if (item.doc_no) parts.push(item.doc_no)
  if (item.step_label) parts.push(item.step_label)
  if (item.age_days != null) parts.push(`停留 ${item.age_days} 天`)
  return parts.join(' · ')
}

/**
 * 工作台条目行：整行可点击跳单据详情。
 *
 * 无 `path` 的条目（如 CAPA 暂无页面）渲染为不可点行并置灰，
 * 不制造「点了没反应」的死链。
 */
export function WorkbenchItemRow({ item, variant = 'todo', isRead = false, actionSlot }: WorkbenchItemRowProps) {
  const meta = buildMeta(item, variant)
  const dotColor = item.overdue
    ? OVERDUE_COLOR
    : variant === 'todo' && item.match_kind === 'person'
      ? 'var(--color-primary)'
      : 'var(--color-hairline-strong)'

  const content = (
    <>
      <span
        aria-hidden
        className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full"
        style={{ backgroundColor: dotColor }}
      />
      <div className="min-w-0 flex-1">
        <div className="flex min-w-0 items-center gap-2">
          <span className="shrink-0 rounded-[4px] bg-[var(--color-surface)] px-1.5 py-0.5 text-[11px] leading-[16px] text-[var(--color-steel)]">
            {item.doc_type_label}
          </span>
          <span className="min-w-0 flex-1 truncate text-[13px] font-medium text-[var(--color-ink)]">
            {item.title}
          </span>
        </div>
        <div className="mt-1 flex min-w-0 items-center gap-x-1.5 text-[12px] text-[var(--color-steel)]">
          {isRead && (
            <span className="shrink-0 rounded-[4px] border border-[var(--color-hairline-strong)] px-1 text-[10px] leading-[14px] text-[var(--color-stone)]">
              已读
            </span>
          )}
          <span className="min-w-0 truncate">{meta}</span>
          {item.overdue && (
            <span className="inline-flex shrink-0 items-center gap-1" style={{ color: OVERDUE_COLOR }}>
              <span aria-hidden className="h-1 w-1 rounded-full" style={{ backgroundColor: OVERDUE_COLOR }} />
              超期
            </span>
          )}
        </div>
      </div>
      {variant === 'todo' && (
        <span
          className={[
            'mt-0.5 shrink-0 rounded-[4px] border px-1.5 py-0.5 text-[11px] leading-[16px]',
            item.match_kind === 'person'
              ? 'border-[var(--color-primary)] text-[var(--color-primary)]'
              : 'border-[var(--color-hairline-strong)] text-[var(--color-steel)]',
            // 有行内操作位时，hover 让出右边缘给按钮（按钮宽度大于标签，避免文字重叠）
            actionSlot ? 'group-hover:invisible' : '',
          ].join(' ')}
        >
          {item.match_kind_label || (item.match_kind === 'person' ? '待我审批' : '同角色待办')}
        </span>
      )}
      {!item.path ? (
        <span className="mt-0.5 shrink-0 text-[11px] text-[var(--color-steel)] opacity-60">暂不可跳转</span>
      ) : actionSlot ? null : (
        <ArrowRightOutlined className="mt-1 shrink-0 text-[12px] text-[var(--color-steel)] opacity-0 transition-opacity group-hover:opacity-100" />
      )}
    </>
  )

  const rowClass = [
    'group flex min-w-0 items-start gap-3 rounded-[var(--rounded-md)] px-3 py-2.5 transition-colors',
    isRead ? 'opacity-60' : '',
  ]
    .filter(Boolean)
    .join(' ')

  const row = !item.path ? (
    <div className={`${rowClass} cursor-default opacity-70`} title="该单据暂无详情页面">
      {content}
    </div>
  ) : (
    <Link
      href={item.path}
      className={`${rowClass} hover:bg-[var(--color-surface)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-[var(--color-primary)]`}
    >
      {content}
    </Link>
  )

  if (!actionSlot) return row

  return (
    <div className="group relative">
      {row}
      <div className="absolute right-2 top-1/2 z-10 -translate-y-1/2">{actionSlot}</div>
    </div>
  )
}