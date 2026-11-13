'use client'

import type { ReactNode } from 'react'
import type { DeviationLedgerDetail } from '@/types/quality'
import {
  isSectionActionable,
  PENDING_TONE,
  SECTION_BY_KEY,
  SECTION_TONE,
  type DeviationSectionKey,
} from './detailSections'

interface SectionCardProps {
  /** 分区 key，同时作为滚动锚点 id，并决定标题、图标与色调 */
  section: DeviationSectionKey
  /**
   * 传入单据详情后，按后端下发的 per-user 权限自动判定「是否待我处理」：
   * 待办 → 主色紫 + 待办标签；否则 → 中性灰。不传则恒为中性。
   */
  ledger?: DeviationLedgerDetail
  /** 标题右侧的状态标签（如「2/3 行已通过」） */
  badge?: ReactNode
  /** 标题区右侧操作按钮 */
  extra?: ReactNode
  children: ReactNode
  className?: string
}

/**
 * 偏差详情页统一板块容器：左侧 3px 色条 + 标题区（图标块 / 标题 / 副标题）+ 头部分隔线。
 * 颜色只表达两种状态 —— 中性（常态）与主色（当前登录人待办），不再按板块区分色相。
 * 用原生 <section> 而非 antd Card，是因为「标题区底色 + 左侧色条」用 Card 需要大量 !important 覆盖。
 */
export function SectionCard({ section, ledger, badge, extra, children, className }: SectionCardProps) {
  const meta = SECTION_BY_KEY[section]
  const Icon = meta.icon
  const pending = ledger ? isSectionActionable(section, ledger) : false
  const tone = pending ? PENDING_TONE : SECTION_TONE
  const showPendingLabel = pending && Boolean(meta.pendingLabel)

  return (
    <section
      id={meta.key}
      className={`relative scroll-mt-6 overflow-hidden rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] shadow-sm${className ? ` ${className}` : ''}`}
    >
      <span className={`absolute inset-y-0 left-0 w-[3px] ${tone.bar}`} aria-hidden />
      <header
        className={`flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-[var(--color-hairline)] py-2.5 pl-4 pr-3 ${tone.headerBg}`}
      >
        <div className="flex min-w-0 items-center gap-2">
          <span
            className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-lg text-[14px] ${tone.iconBox}`}
            aria-hidden
          >
            <Icon />
          </span>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
              <h2 className="text-[15px] font-semibold leading-5 text-[var(--color-ink)]">{meta.label}</h2>
              {showPendingLabel ? (
                <span className="inline-flex items-center rounded-full border border-[#5645D4] bg-[#EBE8FB] px-1.5 text-[11px] font-medium leading-4 text-[#4534B3]">
                  {meta.pendingLabel}
                </span>
              ) : null}
              {badge}
            </div>
            <p className="mt-0.5 text-[12px] leading-4 text-[var(--color-stone)]">{meta.subtitle}</p>
          </div>
        </div>
        {extra ? <div className="flex flex-wrap items-center justify-end gap-2">{extra}</div> : null}
      </header>
      <div className="px-4 py-3">{children}</div>
    </section>
  )
}