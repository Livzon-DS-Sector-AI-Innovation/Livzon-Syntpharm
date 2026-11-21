'use client'

import Link from 'next/link'
import { Empty, Typography } from 'antd'
import type { components } from '@/types/generated/schema'
import { MODULE_PROCESS_PATH } from './constants'
import { WorkbenchItemRow } from './WorkbenchItemRow'

const { Text } = Typography

type ProcessSection = components['schemas']['ProcessSectionModel']

interface ProcessPanelProps {
  section: ProcessSection
  unavailable?: boolean
}

/** 卡片内最多展示条数（超出引导到模块列表页） */
const MAX_VISIBLE = 6

export function ProcessPanel({ section, unavailable }: ProcessPanelProps) {
  const groups = (section.groups ?? []).filter((group) => (group.items?.length ?? 0) > 0)
  const items = groups.flatMap((group) => group.items ?? []).slice(0, MAX_VISIBLE)
  const hiddenCount = groups.reduce((sum, group) => sum + (group.items?.length ?? 0), 0) - items.length
  const links = groups
    .map((group) => ({ key: group.module_key, ...MODULE_PROCESS_PATH[group.module_key] }))
    .filter((entry): entry is { key: string; label: string; path: string } => Boolean(entry.path))

  return (
    <section
      id="home-processes"
      className="flex min-w-0 flex-col overflow-hidden rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-5"
    >
      <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
        <span className="text-[15px] font-semibold text-[var(--color-ink)]">我参与的流程</span>
        {!unavailable && (
          <Text type="secondary" className="text-[12px]">
            共 {section.total}
            {section.has_more ? '+' : ''} 项 · 未完结
          </Text>
        )}
      </div>

      {unavailable ? (
        <div className="flex flex-1 items-center justify-center py-6">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="数据暂时不可用，请稍后刷新" />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-1 items-center justify-center py-6">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无进行中的流程" />
        </div>
      ) : (
        <div className="flex flex-col">
          {items.map((item) => (
            <WorkbenchItemRow key={`${item.source}-${item.id}`} item={item} variant="process" />
          ))}
        </div>
      )}

      {!unavailable && (hiddenCount > 0 || links.length > 0) && (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-[var(--color-hairline-soft)] pt-2">
          <span className="text-[12px] text-[var(--color-steel)]">
            {hiddenCount > 0 ? `另有 ${hiddenCount} 项未展示` : ''}
          </span>
          <span className="flex flex-wrap items-center gap-3 text-[12px]">
            {links.map((entry) => (
              <Link key={entry.key} href={entry.path} className="text-[var(--color-primary)] hover:underline">
                查看{entry.label} →
              </Link>
            ))}
          </span>
        </div>
      )}
    </section>
  )
}