'use client'

import { Empty, Tag, Timeline } from 'antd'
import type { DeviationReviewOpinion } from '@/types/quality'
import { PersonInline } from '../PersonInline'
import { SectionCard } from './SectionCard'

interface ReviewTimelineCardProps {
  opinions: DeviationReviewOpinion[]
}

const RESULT_META: Record<string, { color: string; label: string; tag: string }> = {
  approved: { color: 'green', label: '通过', tag: 'success' },
  rejected: { color: 'red', label: '退回', tag: 'error' },
  resubmitted: { color: 'blue', label: '重新提交', tag: 'processing' },
}

export function ReviewTimelineCard({ opinions }: ReviewTimelineCardProps) {
  const items = [...opinions].reverse()
  return (
    <SectionCard
      section="review-timeline"
      badge={<span className="text-[12px] text-[var(--color-stone)]">共 {items.length} 次</span>}
    >
      {items.length === 0 ? (
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无审核记录" />
      ) : (
        <Timeline
          items={items.map((opinion) => {
            const meta = RESULT_META[opinion.result] ?? { color: 'gray', label: '其他', tag: 'default' }
            return {
              color: meta.color,
              content: (
                <div className="flex flex-col gap-1 text-[13px]">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium text-[var(--color-ink)]">
                      {opinion.step_label || opinion.step}
                    </span>
                    <Tag color={meta.tag}>{meta.label}</Tag>
                    <span className="flex flex-wrap items-center gap-1 text-[12px] text-[var(--color-slate)]">
                      <PersonInline
                        person={{ id: opinion.author_id, name: opinion.author_name, avatar_url: opinion.author_avatar }}
                        avatarSize={20}
                      />
                      <span>· {formatTime(opinion.create_time)}</span>
                    </span>
                  </div>
                  {opinion.content && (
                    <p className="whitespace-pre-wrap break-words text-[13px] leading-5 text-[var(--color-slate)]">
                      {opinion.content}
                    </p>
                  )}
                </div>
              ),
            }
          })}
        />
      )}
    </SectionCard>
  )
}

function formatTime(value?: string | null): string {
  if (!value) return '-'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleString('zh-CN', { hour12: false })
}