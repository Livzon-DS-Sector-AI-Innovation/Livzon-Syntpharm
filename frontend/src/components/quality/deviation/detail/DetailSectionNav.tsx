'use client'

import { CompassOutlined } from '@ant-design/icons'
import type { DeviationLedgerDetail } from '@/types/quality'
import { scrollToSection } from './detailScroll'
import { isSectionActionable, SECTION_TONE, visibleSections } from './detailSections'

interface DetailSectionNavProps {
  ledger: DeviationLedgerDetail
  /** 当前滚动到的板块 id，用于高亮 */
  activeId: string | null
}

/**
 * 分区导航条：常驻但不吸顶（吸顶会遮挡内容、移动端吃掉近三成视口）。
 * 点击平滑滚动到对应板块；无权限/本单不展示的板块按 isSectionVisible 自动隐藏。
 * chip 颜色统一主色（只表达「当前位置」）；当前登录人待办的板块额外带一个主色圆点。
 */
export function DetailSectionNav({ ledger, activeId }: DetailSectionNavProps) {
  const items = visibleSections(ledger)
  if (items.length === 0) return null

  return (
    <nav
      aria-label="页面板块导航"
      className="flex items-center gap-2 rounded-xl border border-[var(--color-hairline)] bg-[var(--color-canvas)] px-3 py-2 shadow-sm"
    >
      <span className="hidden shrink-0 items-center gap-1 text-[12px] text-[var(--color-stone)] sm:flex">
        <CompassOutlined />
        板块
      </span>
      <div className="flex min-w-0 flex-1 items-center gap-1.5 overflow-x-auto pb-0.5 [scrollbar-width:none]">
        {items.map((item) => {
          const Icon = item.icon
          const active = item.key === activeId
          const pending = isSectionActionable(item.key, ledger)
          const base =
            'group inline-flex shrink-0 cursor-pointer items-center whitespace-nowrap rounded-full border px-2.5 py-1 transition-colors'
          const state = active
            ? SECTION_TONE.chipActive
            : `border-[var(--color-hairline)] bg-[var(--color-canvas)] ${SECTION_TONE.chipHoverBorder} hover:bg-[var(--color-surface-soft)]`
          // 文字色/字号落在内层 span：antd reset 的 button{color:inherit;font-size:inherit}
          // 未分层，会盖掉 button 上的 Tailwind 工具类
          return (
            <button
              key={item.key}
              type="button"
              title={pending ? `${item.subtitle}（待我处理：${item.pendingLabel}）` : item.subtitle}
              aria-current={active ? 'true' : undefined}
              className={`${base} ${state}`}
              onClick={() => scrollToSection(item.key)}
            >
              <span
                className={`inline-flex items-center gap-1.5 text-[12px] ${
                  active ? 'text-white' : `text-[var(--color-slate)] ${SECTION_TONE.chipHoverText}`
                }`}
              >
                {pending ? (
                  <span
                    className={`h-1.5 w-1.5 shrink-0 rounded-full ${active ? 'bg-white' : 'bg-[#5645D4]'}`}
                    aria-hidden
                  />
                ) : null}
                <Icon className="text-[12px]" />
                {item.label}
              </span>
            </button>
          )
        })}
      </div>
    </nav>
  )
}