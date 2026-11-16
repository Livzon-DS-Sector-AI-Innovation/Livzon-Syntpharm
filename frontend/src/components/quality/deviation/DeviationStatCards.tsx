'use client'

import Link from 'next/link'
import type { ReactNode } from 'react'
import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  FileTextOutlined,
  RollbackOutlined,
} from '@ant-design/icons'
import type { DeviationLedgerStatistics } from '@/types/quality'
import { DEVIATION_LEDGER_PATH } from './constants'

interface DeviationStatCardsProps {
  statistics: DeviationLedgerStatistics | null
  /** 首屏骨架：父级用 transition 期间保持占位，避免高度跳动 */
  loading?: boolean
}

interface StatCardMeta {
  key: string
  label: string
  hint: string
  value: number
  icon: ReactNode
  accent: string
  /** 只有带单值筛选条件的卡片可下钻；总数与待处理没有对应的单值筛选口径 */
  href: string | null
}

export function DeviationStatCards({ statistics, loading = false }: DeviationStatCardsProps) {
  /** 统计接口失败时显示占位符而不是 0，避免与「统计数据不可用」告警矛盾 */
  const unavailable = statistics === null
  const stats = statistics ?? { total: 0, pending: 0, returned: 0, closed: 0 }

  const cards: StatCardMeta[] = [
    {
      key: 'total',
      label: '偏差总数',
      hint: '全部在册偏差',
      value: stats.total,
      icon: <FileTextOutlined />,
      accent: 'var(--color-primary)',
      href: null,
    },
    {
      key: 'pending',
      label: '待处理',
      hint: '处于审核 / 调查等流转环节',
      value: stats.pending,
      icon: <ClockCircleOutlined />,
      accent: 'var(--color-warning)',
      href: null,
    },
    {
      key: 'returned',
      label: '已退回',
      hint: '已退回，待目标环节重新处理',
      value: stats.returned,
      icon: <RollbackOutlined />,
      accent: 'var(--color-error)',
      href: `${DEVIATION_LEDGER_PATH}?status=returned`,
    },
    {
      key: 'closed',
      label: '已关闭',
      hint: '已完成闭环',
      value: stats.closed,
      icon: <CheckCircleOutlined />,
      accent: 'var(--color-success)',
      href: `${DEVIATION_LEDGER_PATH}?status=closed`,
    },
  ]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      {cards.map((card) => {
        const body = (
          <>
            <div className="flex items-start justify-between">
              <span className="text-[13px] font-medium text-[var(--color-slate)]">{card.label}</span>
              <span
                className="flex h-8 w-8 items-center justify-center rounded-lg text-[15px]"
                style={{ color: card.accent, background: 'var(--color-surface)' }}
              >
                {card.icon}
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              {loading ? (
                <span className="h-7 w-16 animate-pulse rounded bg-[var(--color-surface)]" />
              ) : (
                <span className="text-[28px] font-semibold leading-none text-[var(--color-ink)]">
                  {unavailable ? '-' : card.value}
                </span>
              )}
              {!unavailable && <span className="text-[12px] text-[var(--color-stone)]">条</span>}
            </div>
            <p className="mt-2 line-clamp-2 text-[12px] leading-5 text-[var(--color-stone)]">{card.hint}</p>
            {card.href ? (
              <span className="mt-2 inline-flex items-center gap-1 text-[12px] font-medium text-[var(--color-slate)] transition-colors group-hover:text-[var(--color-primary)]">
                查看看板 →
              </span>
            ) : (
              <span className="mt-2 block h-[18px]" />
            )}
          </>
        )

        const className =
          'rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-4 shadow-[0_1px_2px_rgba(26,26,26,0.04)]'
        // 只有可下钻的卡片才给上浮 / 阴影反馈，其余卡片保持静态，避免看起来可点
        const interactive =
          'group cursor-pointer transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--color-hairline-strong)] hover:shadow-[0_6px_16px_rgba(26,26,26,0.08)]'

        return card.href ? (
          <Link key={card.key} href={card.href} className={`${className} ${interactive}`}>
            {body}
          </Link>
        ) : (
          <div key={card.key} className={className}>
            {body}
          </div>
        )
      })}
    </div>
  )
}