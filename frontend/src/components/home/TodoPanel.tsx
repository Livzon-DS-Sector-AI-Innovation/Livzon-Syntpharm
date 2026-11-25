'use client'

import { useMemo, useState } from 'react'
import Link from 'next/link'
import { Empty, Segmented, Typography } from 'antd'
import type { components } from '@/types/generated/schema'
import { MODULE_HOME_PATH } from './constants'
import { WorkbenchItemRow } from './WorkbenchItemRow'

const { Text } = Typography

type TodoSection = components['schemas']['TodoSectionModel']
type WorkbenchGroup = components['schemas']['WorkbenchGroupModel']

interface TodoPanelProps {
  section: TodoSection
  /** 聚合接口失败：整卡降级为「数据暂时不可用」 */
  unavailable?: boolean
}

/** 卡片内最多展示条数（超出引导到模块列表页） */
const MAX_VISIBLE = 6

export function TodoPanel({ section, unavailable }: TodoPanelProps) {
  const groups = useMemo(() => (section.groups ?? []).filter((group) => (group.items?.length ?? 0) > 0), [section])
  const [active, setActive] = useState<string>('all')

  const visibleGroups = active === 'all' ? groups : groups.filter((group) => group.module_key === active)
  const items = visibleGroups.flatMap((group) => group.items ?? []).slice(0, MAX_VISIBLE)
  const hiddenCount = visibleGroups.reduce((sum, group) => sum + (group.items?.length ?? 0), 0) - items.length
  const filterable = groups.length > 1

  const options = useMemo(
    () => [
      { label: `全部 ${section.total}`, value: 'all' },
      ...groups.map((group: WorkbenchGroup) => ({
        label: `${group.module_label} ${group.count}${group.has_more ? '+' : ''}`,
        value: group.module_key,
      })),
    ],
    [groups, section.total],
  )

  const listLinks = visibleGroups
    .map((group) => ({ key: group.module_key, label: group.module_label, path: MODULE_HOME_PATH[group.module_key] }))
    .filter((entry): entry is { key: string; label: string; path: string } => Boolean(entry.path))

  return (
    <section
      id="home-todos"
      className="flex min-w-0 flex-col overflow-hidden rounded-[var(--rounded-lg)] border border-[var(--color-hairline)] bg-[var(--color-canvas)] p-5"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <span className="text-[15px] font-semibold text-[var(--color-ink)]">审核待办</span>
          {!unavailable && (
            <Text type="secondary" className="text-[12px]">
              共 {section.total}
              {section.has_more ? '+' : ''} 项
              {section.person_total > 0 ? ` · 待我审批 ${section.person_total}` : ''}
            </Text>
          )}
        </div>
        {!unavailable && filterable && (
          <Segmented size="small" options={options} value={active} onChange={(value) => setActive(String(value))} />
        )}
      </div>

      {unavailable ? (
        <div className="flex flex-1 items-center justify-center py-6">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="数据暂时不可用，请稍后刷新" />
        </div>
      ) : items.length === 0 ? (
        <div className="flex flex-1 items-center justify-center py-6">
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无待办" />
        </div>
      ) : (
        <div className="flex flex-col">
          {items.map((item) => (
            <WorkbenchItemRow key={`${item.source}-${item.id}`} item={item} variant="todo" />
          ))}
        </div>
      )}

      {!unavailable && (hiddenCount > 0 || listLinks.length > 0) && (
        <div className="mt-2 flex flex-wrap items-center justify-between gap-2 border-t border-[var(--color-hairline-soft)] pt-2">
          <span className="text-[12px] text-[var(--color-steel)]">
            {hiddenCount > 0 ? `另有 ${hiddenCount} 项未展示` : ''}
          </span>
          <span className="flex flex-wrap items-center gap-3 text-[12px]">
            {listLinks.map((entry) => (
              <Link key={entry.key} href={entry.path} className="text-[var(--color-primary)] hover:underline">
                进入{entry.label} →
              </Link>
            ))}
          </span>
        </div>
      )}
    </section>
  )
}