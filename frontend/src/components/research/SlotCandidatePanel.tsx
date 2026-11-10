'use client'

import { useMemo, useState } from 'react'
import { Button, Empty, Input, Tag, Typography } from 'antd'
import type { DocGenSlotCandidate } from '@/types/research/deliverable-template-slot'

interface Props {
  candidates: DocGenSlotCandidate[]
  /** 已被当前槽位占用的候选位 ID */
  usedIds: Set<string>
  disabled?: boolean
  onPick: (candidate: DocGenSlotCandidate) => void
}

/** 候选面板一次最多渲染的条数：母本可有数百个位置，全量渲染会卡 */
const RENDER_LIMIT = 200

/**
 * 母本候选位置面板：搜索 + 点选绑定。
 *
 * 已被占用的位置不可重复占用（一个位置只能填一个槽位），但仍显示出来，
 * 让用户知道「这个位置 AI 已经认过了」。
 */
export function SlotCandidatePanel({ candidates, usedIds, disabled, onPick }: Props) {
  const [keyword, setKeyword] = useState('')

  const filtered = useMemo(() => {
    const word = keyword.trim().toLowerCase()
    if (!word) return candidates
    return candidates.filter((item) =>
      [item.label, item.text, item.context].some((field) => (field ?? '').toLowerCase().includes(word)),
    )
  }, [candidates, keyword])

  const visible = filtered.slice(0, RENDER_LIMIT)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', minHeight: 0 }}>
      <Input.Search
        allowClear
        placeholder="搜索位置名称，或粘贴一段原文来找"
        value={keyword}
        onChange={(e) => setKeyword(e.target.value)}
        style={{ marginBottom: 8 }}
      />
      <Typography.Text type="secondary" style={{ fontSize: 12, marginBottom: 8 }}>
        共 {candidates.length} 个可填位置，当前显示 {filtered.length} 个
        {filtered.length > RENDER_LIMIT ? `（仅前 ${RENDER_LIMIT} 个可点选）` : ''}
      </Typography.Text>
      <div style={{ flex: 1, overflowY: 'auto', border: '1px solid #f0f0f0', borderRadius: 6 }}>
        {visible.length === 0 ? (
          <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="没有找到匹配的位置，换个关键词试试" style={{ margin: 24 }} />
        ) : (
          visible.map((item) => {
            const used = usedIds.has(item.candidate_id)
            return (
              <Button
                key={item.candidate_id}
                type="text"
                block
                disabled={disabled || used}
                onClick={() => onPick(item)}
                style={{
                  height: 'auto',
                  padding: '8px 10px',
                  textAlign: 'left',
                  borderBottom: '1px solid #f5f5f5',
                  borderRadius: 0,
                  whiteSpace: 'normal',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
                  <span style={{ fontSize: 12, fontWeight: 500 }}>{item.label}</span>
                  {used ? <Tag style={{ marginInlineEnd: 0 }}>已有填充项</Tag> : null}
                </div>
                <div style={{ fontSize: 12, color: '#8c8c8c', marginTop: 2 }}>
                  {(item.text || item.context || '（空白位置）').slice(0, 60)}
                </div>
              </Button>
            )
          })
        )}
      </div>
    </div>
  )
}